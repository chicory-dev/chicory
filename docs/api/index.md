# API Reference

Complete API reference for Chicory — auto-generated from source code docstrings.

## Core Classes

- [Chicory](chicory.md) — Main application class for creating task queues
- [Task](task.md) — Task wrapper providing invocation APIs
- [Worker](worker.md) — Worker process for executing tasks
- [AsyncResult](async-result.md) — Asynchronous result handler
- [TaskContext](task.md#chicory.TaskContext) — Runtime context injected into tasks

## Configuration

- [ChicoryConfig](chicory.md#chicory.ChicoryConfig) — Main configuration class
- [WorkerConfig](worker.md#chicory.WorkerConfig) — Worker-specific configuration
- [RedisBrokerConfig](chicory.md#chicory.config.RedisBrokerConfig) — Redis broker configuration
- [RabbitMQBrokerConfig](chicory.md#chicory.config.RabbitMQBrokerConfig) — RabbitMQ broker configuration
- [RedisBackendConfig](chicory.md#chicory.config.RedisBackendConfig) — Redis backend configuration
- [PostgresBackendConfig](chicory.md#chicory.config.PostgresBackendConfig) — PostgreSQL backend configuration

## Types and Enums

- [Types](types.md) — All enums and data models
- [Exceptions](exceptions.md) — All exception classes
