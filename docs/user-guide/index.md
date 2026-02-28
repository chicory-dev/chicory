# User Guide

Welcome to the Chicory User Guide! This comprehensive guide will help you master all aspects of Chicory, from basic task creation to advanced production deployment.

## What You'll Learn

This guide is organized into several key sections to help you progressively build your knowledge:

### Core Concepts

<div class="grid cards" markdown>

-   :material-cog:{ .lg .middle } **Workers**

    ---

    Understand worker lifecycle, scaling strategies, and deployment options.

    [:octicons-arrow-right-24: Worker Guide](workers.md)

-   :material-application-settings:{ .lg .middle } **Configuration**

    ---

    Master Chicory's flexible configuration system and environment variables.

    [:octicons-arrow-right-24: Configuration Guide](configuration.md)

</div>

### Infrastructure

<div class="grid cards" markdown>

-   :material-message-arrow-right:{ .lg .middle } **Message Brokers**

    ---

    Choose and configure the right message broker for your use case.

    [:octicons-arrow-right-24: Broker Overview](brokers/index.md)

-   :material-database:{ .lg .middle } **Result Backends**

    ---

    Store and retrieve task results with various backend options.

    [:octicons-arrow-right-24: Backend Overview](backends/index.md)

</div>

## Quick Navigation

### By Use Case

- **Getting Started**: Start with the [Workers guide](workers.md) and [Tutorial](../tutorial/index.md)
- **Production Deployment**: Review [Configuration](configuration.md) and broker setup ([Redis](brokers/redis.md) or [RabbitMQ](brokers/rabbitmq.md))
- **Reliability**: See [Retry Policies](../tutorial/retry-policies.md) for retry strategies and dead-letter queues
- **Performance**: Check [Workers](workers.md) for scaling and [Configuration](configuration.md) for optimization

### By Component

#### Brokers
- [Broker Overview](brokers/index.md) - Understanding message brokers
- [Redis Broker](brokers/redis.md) - Redis Streams setup and configuration
- [RabbitMQ Broker](brokers/rabbitmq.md) - RabbitMQ setup and advanced features

#### Backends
- [Backend Overview](backends/index.md) - Understanding result backends
- [Redis Backend](backends/redis.md) - Redis backend for fast results
- [PostgreSQL Backend](backends/postgres.md) - Persistent storage with PostgreSQL

## Getting Help

If you get stuck, here are some resources:

- **Examples**: Check out our [examples directory](https://github.com/chicory-dev/chicory/tree/main/examples) for working code
- **Tutorial**: Follow the [step-by-step tutorial](../tutorial/basic-usage.md) for guided learning
- **API Reference**: See the [API documentation](../api/index.md) for detailed reference
- **GitHub Issues**: Report bugs or request features on [GitHub](https://github.com/chicory-dev/chicory/issues)

## Documentation Conventions

Throughout this guide, we use the following conventions:

!!! tip "Tips"
    Helpful suggestions and best practices appear in tip boxes like this.

!!! warning "Warnings"
    Important warnings about potential issues appear like this.

!!! info "Information"
    Additional context and explanations appear in info boxes.

!!! example "Examples"
    Code examples and practical demonstrations appear like this.

Code blocks show both synchronous and asynchronous examples where relevant:

```python
# Async example (recommended)
async def my_task():
    await something()
```

```python
# Sync example (also supported)
def my_task():
    something()
```

Environment variables are shown in uppercase:

```bash
CHICORY_BROKER_REDIS_HOST=localhost
CHICORY_WORKER_CONCURRENCY=16
```

Let's get started! Begin with the [Workers guide](workers.md) to learn how to run background jobs, or check the [Tutorial](../tutorial/index.md) for a step-by-step introduction.
