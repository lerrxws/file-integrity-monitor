package config

import (
	"fmt"
	"os"
	"strings"

	"gopkg.in/yaml.v3"
)

type Config struct {
	Monitor  MonitorConfig  `yaml:"monitor"`
	Storage  StorageConfig  `yaml:"storage"`
	Database DatabaseConfig `yaml:"database"`
	Logging  LoggingConfig  `yaml:"logging"`
	Alert    AlertConfig    `yaml:"alert"`
}

type MonitorConfig struct {
	File string `yaml:"file"`
}

type StorageConfig struct {
	DataDir string `yaml:"data_dir"`
}

type DatabaseConfig struct {
	Driver string `yaml:"driver"`
	Path   string `yaml:"path"`
}

type LoggingConfig struct {
	Path string `yaml:"path"`
}

type AlertConfig struct {
	Type string `yaml:"type"`
}

func Load(path string) (*Config, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, fmt.Errorf("open config %q: %w", path, err)
	}
	defer file.Close()

	var config Config
	decoder := yaml.NewDecoder(file)
	decoder.KnownFields(true)

	if err := decoder.Decode(&config); err != nil {
		return nil, fmt.Errorf("decode config %q: %w", path, err)
	}

	if err := config.Validate(); err != nil {
		return nil, fmt.Errorf("validate config %q: %w", path, err)
	}

	return &config, nil
}

func (c Config) Validate() error {
	requiredValues := map[string]string{
		"monitor.file":     c.Monitor.File,
		"storage.data_dir": c.Storage.DataDir,
		"database.driver":  c.Database.Driver,
		"database.path":    c.Database.Path,
		"logging.path":     c.Logging.Path,
		"alert.type":       c.Alert.Type,
	}

	for field, value := range requiredValues {
		if strings.TrimSpace(value) == "" {
			return fmt.Errorf("%s is required", field)
		}
	}

	return nil
}
