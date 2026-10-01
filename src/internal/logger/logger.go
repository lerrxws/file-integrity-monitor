package logger

import (
	"io"
	"log/slog"
	"os"
)

func New(path string) (*slog.Logger, *os.File, error) {
	file, err := os.OpenFile(
		path,
		os.O_CREATE|os.O_APPEND|os.O_WRONLY,
		0o644,
	)
	if err != nil {
		return nil, nil, err
	}

	writer := io.MultiWriter(os.Stdout, file)

	handler := slog.NewTextHandler(writer, &slog.HandlerOptions{
		Level: slog.LevelInfo,
	})

	log := slog.New(handler)

	return log, file, nil
}