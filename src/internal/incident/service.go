package incident

import "time"

type Incident struct {
	Path         string
	ExpectedHash string
	ActualHash   string
	DetectedAt   time.Time
}

func New(path, expectedHash, actualHash string) Incident {
	return Incident{
		Path:         path,
		ExpectedHash: expectedHash,
		ActualHash:   actualHash,
		DetectedAt:   time.Now(),
	}
}