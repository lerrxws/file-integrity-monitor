package config

import (
	"os"
	"gopkg.in/yaml.v3"
)

type Config struct {
	Monitor struct {
		File string `yaml:"file"`
	} `yaml:"monitor"`
	
	Storage struct {
		DataDir      string      `yaml:"data_dir"`
	} `yaml:"storage"`

	Database struct {
		Driver string `yaml:"driver"`
		Path   string `yaml:"path"`
	} `yaml:"database"`

	Logging struct {
		Path string `yaml:"path"`
	} `yaml:"logging"`

	Alert struct {
		Type string `yaml:"type"`
	} `yaml:"alert"`
}

func Load(path string) (*Config, error) {

	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var config Config
	if err := yaml.Unmarshal(data, &config); err != nil {
		return nil, err
	}
	return &config, nil

}