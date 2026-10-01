package baseline

import (
	"context"
	"database/sql"
	"errors"
	"fmt"

	"github.com/lerrxws/file-integrity-monitor/internal/monitor"
)

type Repository struct {
	db *sql.DB
}

func NewRepository(db *sql.DB) *Repository {
	return &Repository{db: db}
}

func (r *Repository) Init(ctx context.Context) error {
	_, err := r.db.ExecContext(ctx, `
		CREATE TABLE IF NOT EXISTS baselines (
			path TEXT PRIMARY KEY,
			hash TEXT NOT NULL
		)
	`)
	if err != nil {
		return fmt.Errorf("initialize baseline repository: %w", err)
	}

	return nil
}

func (r *Repository) Save(ctx context.Context, baseline monitor.Baseline) error {
	_, err := r.db.ExecContext(ctx, `
		INSERT INTO baselines (path, hash)
		VALUES (?, ?)
		ON CONFLICT(path)
		DO UPDATE SET hash = excluded.hash
	`, baseline.Path, baseline.Hash)
	if err != nil {
		return fmt.Errorf("save baseline for %q: %w", baseline.Path, err)
	}

	return nil
}

func (r *Repository) Get(ctx context.Context, path string) (*monitor.Baseline, error) {
	var baseline monitor.Baseline

	err := r.db.QueryRowContext(ctx, `
		SELECT path, hash
		FROM baselines
		WHERE path = ?
	`, path).Scan(&baseline.Path, &baseline.Hash)

	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("get baseline for %q: %w", path, err)
	}

	return &baseline, nil
}
