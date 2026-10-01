package fim

import (
	"fmt"
	"log/slog"

	"github.com/fsnotify/fsnotify"

	"github.com/lerrxws/file-integrity-monitor/internal/alert"
	"github.com/lerrxws/file-integrity-monitor/internal/baseline"
	"github.com/lerrxws/file-integrity-monitor/internal/incident"
	"github.com/lerrxws/file-integrity-monitor/internal/integrity"
	"github.com/lerrxws/file-integrity-monitor/internal/watcher"
)

type Service struct {
	filePath     string
	repository   baseline.Repository
	logger       *slog.Logger
	alertService alert.Service
}

func NewService(
	filePath string,
	repository baseline.Repository,
	logger *slog.Logger,
	alertService alert.Service,
) *Service {
	return &Service{
		filePath:     filePath,
		repository:   repository,
		logger:       logger,
		alertService: alertService,
	}
}

func (s *Service) Run() error {
	if err := s.ensureBaseline(); err != nil {
		return err
	}

	if err := s.checkIntegrity(); err != nil {
		return err
	}

	return s.watch()
}

func (s *Service) ensureBaseline() error {
	storedBaseline, err := s.repository.Get(s.filePath)
	if err != nil {
		return err
	}

	if storedBaseline != nil {
		return nil
	}

	currentHash, err := integrity.CalculateSHA256(s.filePath)
	if err != nil {
		return err
	}

	newBaseline := baseline.Baseline{
		Path: s.filePath,
		Hash: currentHash,
	}

	if err := s.repository.Save(newBaseline); err != nil {
		return err
	}

	s.logger.Info(
		"baseline created",
		"path", s.filePath,
	)

	return nil
}

func (s *Service) checkIntegrity() error {
	storedBaseline, err := s.repository.Get(s.filePath)
	if err != nil {
		return err
	}

	result, err := integrity.Check(
		s.filePath,
		storedBaseline.Hash,
	)
	if err != nil {
		return err
	}

	if !result.Modified {
		s.logger.Info(
			"file integrity OK",
			"path", s.filePath,
		)

		return nil
	}

	s.handleIncident(
		storedBaseline.Hash,
		result.CurrentHash,
	)

	return nil
}

func (s *Service) handleIncident(expectedHash, actualHash string) {
	detectedIncident := incident.New(
		s.filePath,
		expectedHash,
		actualHash,
	)

	s.logger.Warn(
		"integrity incident detected",
		"path", detectedIncident.Path,
		"expected_hash", detectedIncident.ExpectedHash,
		"actual_hash", detectedIncident.ActualHash,
	)

	message := fmt.Sprintf(
		"File integrity violation detected: %s",
		detectedIncident.Path,
	)

	if err := s.alertService.Send(message); err != nil {
		s.logger.Error(
			"failed to send alert",
			"path", detectedIncident.Path,
			"error", err,
		)
	}
}

func (s *Service) watch() error {
	fileWatcher, err := watcher.New()
	if err != nil {
		return err
	}
	defer fileWatcher.Close()

	if err := fileWatcher.Add(s.filePath); err != nil {
		return err
	}

	s.logger.Info(
		"watching file",
		"path", s.filePath,
	)

	for {
		select {
		case event := <-fileWatcher.Events():
			if event.Op&fsnotify.Write == 0 {
				continue
			}

			if err := s.checkIntegrity(); err != nil {
				s.logger.Error(
					"integrity check failed",
					"path", s.filePath,
					"error", err,
				)
			}

		case err := <-fileWatcher.Errors():
			s.logger.Error(
				"watcher error",
				"error", err,
			)
		}
	}
}