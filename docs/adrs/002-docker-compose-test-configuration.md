# ADR-002: Docker Compose Test Configuration

## Status
Proposed

## Context
During end-to-end testing, the Qdrant container (`mcp-test-qdrant-1`) fails to start properly and is marked as unhealthy. This causes test failures and requires manual intervention to start the container. The issue stems from differences between the production and test Docker Compose configurations.

## Decision
We will align the test Docker Compose configuration with the production configuration by:

1. Adding health check configuration for the Qdrant service in test environment
2. Implementing proper service dependency conditions
3. Adjusting storage configuration for test environment
4. Adding appropriate startup delays and retry mechanisms

### Changes Required
1. Update `docker-compose.test.yml`:
   - Add health check configuration for Qdrant
   - Configure service dependencies with health checks
   - Optimize tmpfs configuration for test environment
   - Add appropriate environment variables for Qdrant initialization

2. Update test scripts to handle container startup more gracefully:
   - Add retry logic for service initialization
   - Implement proper cleanup procedures
   - Add detailed logging for troubleshooting

## Consequences

### Positive
- More reliable test execution
- No need for manual intervention
- Consistent behavior between production and test environments
- Better error detection and reporting

### Negative
- Slightly longer test startup time due to health checks
- Additional configuration maintenance
- Increased complexity in test setup

## Implementation Notes
1. Update `docker-compose.test.yml` with health check configuration
2. Modify test scripts to handle container startup
3. Document container requirements and startup procedures
4. Add monitoring for container health in CI/CD pipeline

## References
1. Docker Compose healthcheck documentation
2. Qdrant container requirements
3. Testing best practices for containerized services 