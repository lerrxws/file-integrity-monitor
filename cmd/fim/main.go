package main

import (
	"context"
	"database/sql"
	"flag"
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"

	_ "modernc.org/sqlite"

	"github.com/lerrxws/file-integrity-monitor/internal/alert"
	"github.com/lerrxws/file-integrity-monitor/internal/baseline"
	"github.com/lerrxws/file-integrity-monitor/internal/config"
	"github.com/lerrxws/file-integrity-monitor/internal/filesystem"
	"github.com/lerrxws/file-integrity-monitor/internal/logging"
	"github.com/lerrxws/file-integrity-monitor/internal/monitor"
)

const directoryMode = 0o700

func main() {
	if err := run(); err != nil {
		log.Printf("file integrity monitor failed: %v", err)
		os.Exit(1)
	}
}

func run() error {
	configPath := flag.String("config", "./config/config.yaml", "path to the configuration file")
	flag.Parse()

	ctx, stop := signal.NotifyContext(
		context.Background(),
		os.Interrupt,
		syscall.SIGTERM,
	)
	defer stop()

	cfg, err := config.Load(*configPath)
	if err != nil {
		return err
	}

	if cfg.Alert.Type != "console" {
		return fmt.Errorf("unsupported alert type %q", cfg.Alert.Type)
	}

	if err := os.MkdirAll(cfg.Storage.DataDir, directoryMode); err != nil {
		return fmt.Errorf("create data directory %q: %w", cfg.Storage.DataDir, err)
	}

	db, err := sql.Open(cfg.Database.Driver, cfg.Database.Path)
	if err != nil {
		return fmt.Errorf("open database: %w", err)
	}
	defer db.Close()

	db.SetMaxOpenConns(1)

	if err := db.PingContext(ctx); err != nil {
		return fmt.Errorf("connect to database: %w", err)
	}

	repository := baseline.NewRepository(db)
	if err := repository.Init(ctx); err != nil {
		return err
	}

	appLogger, logFile, err := logging.New(cfg.Logging.Path)
	if err != nil {
		return err
	}
	defer logFile.Close()

	fileWatcher, err := filesystem.NewWatcher()
	if err != nil {
		return err
	}

	service := monitor.New(
		cfg.Monitor.File,
		repository,
		filesystem.NewSHA256Hasher(),
		fileWatcher,
		alert.NewConsole(appLogger),
		appLogger,
	)

	return service.Run(ctx)
}
