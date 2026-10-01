package integrity

type Result struct {
	Modified    bool
	CurrentHash string
}

func Check(path, baselineHash string) (Result, error) {
	currentHash, err := CalculateSHA256(path)
	if err != nil {
		return Result{}, err
	}

	return Result{
		Modified:    currentHash != baselineHash,
		CurrentHash: currentHash,
	}, nil
}