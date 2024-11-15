services:
  # Define the Streamlit application service
  streamlit-app:
    build:
      context: ./  # Set the build context to the current directory
      dockerfile: Dockerfile  # Specify the Dockerfile to use for building the image
      args:
        # Pass build-time arguments to the Dockerfile, used for configuring GuardRails and OpenAI
        GUARDRAILS_TOKEN: ${GUARDRAILS_TOKEN}
        OPENAI_API_KEY: ${OPENAI_API_KEY}
    environment:
      # Set environment variables to be used by the running container
      - COLLECTOR_ENDPOINT=http://phoenix:6006/v1/traces  # Endpoint for tracing data, used by Phoenix
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - GUARDRAILS_TOKEN=${GUARDRAILS_TOKEN}
    ports:
      # Map port 8080 of the container to port 8080 on the host machine
      - "8080:8080"
    volumes:
      # Mount the source code and configuration into the container
      - ./src:/app/src  # Mount the local `src` directory to `/app/src` in the container
      - ./.streamlit:/app/.streamlit  # Mount the Streamlit configuration directory
    healthcheck:
      # Define a health check to verify that the application is running
      test: ["CMD", "wget", "--spider", "http://0.0.0.0:8080/healthz"]  # Use wget to check if the health endpoint is available
      interval: 3s  # Run the health check every 3 seconds
      timeout: 1s  # Timeout for the health check command is 1 second
      retries: 3  # Retry the health check up to 3 times before marking the container as unhealthy
    depends_on:
      # Ensure that the Phoenix service is started before the Streamlit app
      - phoenix

  # Define the Phoenix service for tracing and monitoring
  phoenix:
    image: arizephoenix/phoenix:latest  # Use the latest version of the Phoenix image
    ports:
      - "6006:6006"  # Expose port 6006 for the UI and OTLP HTTP collector
      - "4317:4317"  # Expose port 4317 for OTLP gRPC collector

  # Add Redis
  redis:
    image: redis/redis-stack:latest
    ports:
      - "6379:6379"
