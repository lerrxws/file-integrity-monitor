package alert

import (
	"context"
	"log/slog"

	"github.com/lerrxws/file-integrity-monitor/internal/monitor"
)

type Console struct {
	logger *slog.Logger
}

func NewConsole(logger *slog.Logger) *Console {
	return &Console{logger: logger}
}

func (c *Console) Send(ctx context.Context, incident monitor.Incident) error {
	c.logger.WarnContext(
		ctx,
		"alert sent",
		"message", "File integrity violation detected: "+incident.Path,
		"path", incident.Path,
		"detected_at", incident.DetectedAt,
	)

	return nil
}
