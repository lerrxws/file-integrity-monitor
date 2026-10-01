package filesystem

import (
	"fmt"
	"sync"

	"github.com/fsnotify/fsnotify"

	"github.com/lerrxws/file-integrity-monitor/internal/monitor"
)

type Watcher struct {
	watcher *fsnotify.Watcher
	events  chan monitor.FileEvent
	errors  chan error
	done    chan struct{}
	once    sync.Once
}

func NewWatcher() (*Watcher, error) {
	fileWatcher, err := fsnotify.NewWatcher()
	if err != nil {
		return nil, fmt.Errorf("create file watcher: %w", err)
	}

	watcher := &Watcher{
		watcher: fileWatcher,
		events:  make(chan monitor.FileEvent),
		errors:  make(chan error),
		done:    make(chan struct{}),
	}

	go watcher.forwardEvents()

	return watcher, nil
}

func (w *Watcher) Add(path string) error {
	if err := w.watcher.Add(path); err != nil {
		return fmt.Errorf("add %q to watcher: %w", path, err)
	}

	return nil
}

func (w *Watcher) Events() <-chan monitor.FileEvent {
	return w.events
}

func (w *Watcher) Errors() <-chan error {
	return w.errors
}

func (w *Watcher) Close() error {
	var closeErr error

	w.once.Do(func() {
		close(w.done)
		closeErr = w.watcher.Close()
	})

	return closeErr
}

func (w *Watcher) forwardEvents() {
	defer close(w.events)
	defer close(w.errors)

	for {
		select {
		case <-w.done:
			return

		case event, ok := <-w.watcher.Events:
			if !ok {
				return
			}

			if event.Op&fsnotify.Write == 0 {
				continue
			}

			convertedEvent := monitor.FileEvent{
				Path:      event.Name,
				Operation: monitor.OperationWrite,
			}

			select {
			case w.events <- convertedEvent:
			case <-w.done:
				return
			}

		case err, ok := <-w.watcher.Errors:
			if !ok {
				return
			}

			select {
			case w.errors <- err:
			case <-w.done:
				return
			}
		}
	}
}
