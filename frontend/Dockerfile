FROM nginx:alpine

# Remove default nginx static assets
RUN rm -rf /usr/share/nginx/html/*

# Copy static frontend files
COPY index.html /usr/share/nginx/html/
COPY app.js /usr/share/nginx/html/

# Expose port
EXPOSE 80

# Command to run Nginx (inherited from base image)
CMD ["nginx", "-g", "daemon off;"]
