package monitor

import "context"

type BaselineRepository interface {
	Get(ctx context.Context, path string) (*Baseline, error)
	Save(ctx context.Context, baseline Baseline) error
}

type Hasher interface {
	Calculate(ctx context.Context, path string) (string, error)
}

type Watcher interface {
	Add(path string) error
	Events() <-chan FileEvent
	Errors() <-chan error
	Close() error
}

type Notifier interface {
	Send(ctx context.Context, incident Incident) error
}
