package main

import (
	"database/sql"
	"log"
	"os"

	_ "modernc.org/sqlite"

	"github.com/lerrxws/file-integrity-monitor/internal/alert"
	"github.com/lerrxws/file-integrity-monitor/internal/baseline"
	"github.com/lerrxws/file-integrity-monitor/internal/config"
	"github.com/lerrxws/file-integrity-monitor/internal/fim"
	"github.com/lerrxws/file-integrity-monitor/internal/logger"
)

const (
	directoryMode = 0o755 // rwxr-xr-x
)

func main() {
	cfg, err := config.Load("./config/config.yaml")
	if err != nil {
		log.Fatal(err)
	}

	if err := os.MkdirAll(cfg.Storage.DataDir, directoryMode); err != nil {
		log.Fatal(err)
	}

	db, err := sql.Open(cfg.Database.Driver, cfg.Database.Path)
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	repository := baseline.NewSQLiteRepository(db)

	if err := repository.Init(); err != nil {
		log.Fatal(err)
	}

	appLogger, logFile, err := logger.New(cfg.Logging.Path)
	if err != nil {
		log.Fatal(err)
	}
	defer logFile.Close()

	alertService := alert.NewConsoleService(appLogger)

	service := fim.NewService(
		cfg.Monitor.File,
		repository,
		appLogger,
		alertService,
	)

	if err := service.Run(); err != nil {
		log.Fatal(err)
	}
}