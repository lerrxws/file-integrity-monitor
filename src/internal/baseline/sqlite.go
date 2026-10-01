package baseline

import (
	"database/sql"
	"errors"
)

type SQLiteRepository struct {
	db *sql.DB
}

func NewSQLiteRepository(db *sql.DB) *SQLiteRepository {
	return &SQLiteRepository{
		db: db,
	}
}

func (r *SQLiteRepository) Init() error {
	_, err := r.db.Exec(`
		CREATE TABLE IF NOT EXISTS baselines (
			path TEXT PRIMARY KEY,
			hash TEXT NOT NULL
		)
	`)

	return err
}

func (r *SQLiteRepository) Save(baseline Baseline) error {
	_, err := r.db.Exec(`
		INSERT INTO baselines (path, hash)
		VALUES (?, ?)
		ON CONFLICT(path)
		DO UPDATE SET hash = excluded.hash
	`,
		baseline.Path,
		baseline.Hash,
	)

	return err
}

func (r *SQLiteRepository) Get(path string) (*Baseline, error) {
	var baseline Baseline
	err := r.db.QueryRow(`
		SELECT path, hash
		FROM baselines
		WHERE path = ?
	`, path).Scan(
		&baseline.Path,
		&baseline.Hash,
	)

	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return nil, nil
		}
		return nil, err
	}

	return &baseline, nil
}
