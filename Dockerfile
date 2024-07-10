@injectAtLine:29
# Create a directory for static files
RUN mkdir -p /app/static

# Copy static files
COPY static /app/static