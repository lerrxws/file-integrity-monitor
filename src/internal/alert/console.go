package alert

import "log/slog"

type ConsoleService struct {
	logger *slog.Logger
}

func NewConsoleService(logger *slog.Logger) *ConsoleService {
	return &ConsoleService{
		logger: logger,
	}
}

func (s *ConsoleService) Send(message string) error {
	s.logger.Warn("alert sent", "message", message)
	return nil
}