FROM nginx:alpine

# Copy custom reverse proxy configuration into Nginx configuration directory
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
