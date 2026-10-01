package alert

type Service interface {
	Send(message string) error
}