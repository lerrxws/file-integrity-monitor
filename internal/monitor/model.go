package monitor

import "time"

type Baseline struct {
	Path string
	Hash string
}

type Incident struct {
	Path         string
	ExpectedHash string
	ActualHash   string
	DetectedAt   time.Time
}

type Operation uint8

const (
	OperationWrite Operation = 1 << iota
)

type FileEvent struct {
	Path      string
	Operation Operation
}
