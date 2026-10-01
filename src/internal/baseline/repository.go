package baseline

type Repository interface {
	Get(path string) (*Baseline, error)
	Save(baseline Baseline) error
}
