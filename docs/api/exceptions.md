# Exceptions

Exception hierarchy:

```
ChicoryError (base)
├── TaskNotFoundError
├── ValidationError
├── RetryError
├── MaxRetriesExceededError
├── BackendNotConfiguredError
├── BrokerConnectionError
└── DbPoolExhaustedException
```

::: chicory.ChicoryError
    options:
      heading_level: 2

::: chicory.TaskNotFoundError
    options:
      heading_level: 2

::: chicory.ValidationError
    options:
      heading_level: 2

::: chicory.RetryError
    options:
      heading_level: 2

::: chicory.MaxRetriesExceededError
    options:
      heading_level: 2

::: chicory.BackendNotConfiguredError
    options:
      heading_level: 2

::: chicory.BrokerConnectionError
    options:
      heading_level: 2

::: chicory.DbPoolExhaustedException
    options:
      heading_level: 2
