FROM nginx:alpine

# Copy static frontend files to Nginx html directory
COPY frontend/ /usr/share/nginx/html/

# Copy custom Nginx configuration to override default
COPY nginx.conf /etc/nginx/nginx.conf

# Expose HTTP port
EXPOSE 80

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]