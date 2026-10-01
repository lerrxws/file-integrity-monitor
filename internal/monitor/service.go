package monitor

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"time"
)

var ErrBaselineNotFound = errors.New("baseline not found")

type Service struct {
	filePath   string
	repository BaselineRepository
	hasher     Hasher
	watcher    Watcher
	notifier   Notifier
	logger     *slog.Logger
}

func New(
	filePath string,
	repository BaselineRepository,
	hasher Hasher,
	watcher Watcher,
	notifier Notifier,
	logger *slog.Logger,
) *Service {
	return &Service{
		filePath:   filePath,
		repository: repository,
		hasher:     hasher,
		watcher:    watcher,
		notifier:   notifier,
		logger:     logger,
	}
}

func (s *Service) Run(ctx context.Context) error {
	defer s.watcher.Close()

	if err := s.ensureBaseline(ctx); err != nil {
		return fmt.Errorf("ensure baseline: %w", err)
	}

	if err := s.checkIntegrity(ctx); err != nil {
		return fmt.Errorf("check integrity: %w", err)
	}

	return s.watch(ctx)
}

func (s *Service) ensureBaseline(ctx context.Context) error {
	storedBaseline, err := s.repository.Get(ctx, s.filePath)
	if err != nil {
		return err
	}

	if storedBaseline != nil {
		return nil
	}

	currentHash, err := s.hasher.Calculate(ctx, s.filePath)
	if err != nil {
		return err
	}

	newBaseline := Baseline{
		Path: s.filePath,
		Hash: currentHash,
	}

	if err := s.repository.Save(ctx, newBaseline); err != nil {
		return err
	}

	s.logger.InfoContext(ctx, "baseline created", "path", s.filePath)

	return nil
}

func (s *Service) checkIntegrity(ctx context.Context) error {
	storedBaseline, err := s.repository.Get(ctx, s.filePath)
	if err != nil {
		return err
	}

	if storedBaseline == nil {
		return ErrBaselineNotFound
	}

	currentHash, err := s.hasher.Calculate(ctx, s.filePath)
	if err != nil {
		return err
	}

	if currentHash == storedBaseline.Hash {
		s.logger.InfoContext(ctx, "file integrity OK", "path", s.filePath)
		return nil
	}

	s.handleIncident(ctx, storedBaseline.Hash, currentHash)

	return nil
}

func (s *Service) handleIncident(ctx context.Context, expectedHash, actualHash string) {
	incident := Incident{
		Path:         s.filePath,
		ExpectedHash: expectedHash,
		ActualHash:   actualHash,
		DetectedAt:   time.Now(),
	}

	s.logger.WarnContext(
		ctx,
		"integrity incident detected",
		"path", incident.Path,
		"expected_hash", incident.ExpectedHash,
		"actual_hash", incident.ActualHash,
		"detected_at", incident.DetectedAt,
	)

	if err := s.notifier.Send(ctx, incident); err != nil {
		s.logger.ErrorContext(
			ctx,
			"failed to send alert",
			"path", incident.Path,
			"error", err,
		)
	}
}

func (s *Service) watch(ctx context.Context) error {
	if err := s.watcher.Add(s.filePath); err != nil {
		return fmt.Errorf("watch %q: %w", s.filePath, err)
	}

	s.logger.InfoContext(ctx, "watching file", "path", s.filePath)

	events := s.watcher.Events()
	errorsChannel := s.watcher.Errors()

	for {
		select {
		case <-ctx.Done():
			s.logger.Info("monitor stopped", "path", s.filePath)
			return nil

		case event, ok := <-events:
			if !ok {
				return errors.New("watcher events channel closed")
			}

			if event.Operation&OperationWrite == 0 {
				continue
			}

			if err := s.checkIntegrity(ctx); err != nil {
				s.logger.ErrorContext(
					ctx,
					"integrity check failed",
					"path", event.Path,
					"error", err,
				)
			}

		case err, ok := <-errorsChannel:
			if !ok {
				errorsChannel = nil
				continue
			}

			s.logger.ErrorContext(ctx, "watcher error", "error", err)
		}
	}
}
