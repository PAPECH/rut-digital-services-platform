FROM node:20-alpine AS build
WORKDIR /app
ARG VITE_API_URL=
ARG VITE_WEBAPP_URL=
ARG VITE_MAX_BOT_USERNAME=
ARG VITE_SITE_URL=
ARG VITE_BOT_SLUG=default

ENV VITE_API_URL=$VITE_API_URL
ENV VITE_WEBAPP_URL=$VITE_WEBAPP_URL
ENV VITE_MAX_BOT_USERNAME=$VITE_MAX_BOT_USERNAME
ENV VITE_SITE_URL=$VITE_SITE_URL
ENV VITE_BOT_SLUG=$VITE_BOT_SLUG

COPY package.json ./
RUN npm install --no-audit --no-fund
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
