package logging

import (
	"fmt"
	"io"
	"log/slog"
	"os"
)

func New(path string) (*slog.Logger, io.Closer, error) {
	file, err := os.OpenFile(
		path,
		os.O_CREATE|os.O_APPEND|os.O_WRONLY,
		0o600,
	)
	if err != nil {
		return nil, nil, fmt.Errorf("open log file %q: %w", path, err)
	}

	writer := io.MultiWriter(os.Stdout, file)
	handler := slog.NewTextHandler(writer, &slog.HandlerOptions{
		Level: slog.LevelInfo,
	})

	return slog.New(handler), file, nil
}
