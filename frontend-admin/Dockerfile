FROM node:20-alpine AS build
WORKDIR /app

ARG MAX_BOT_USERNAME
ARG PUBLIC_MINIAPP_URL

ARG VITE_MAX_BOT_USERNAME=$MAX_BOT_USERNAME
ARG VITE_MINIAPP_URL=$PUBLIC_MINIAPP_URL

ENV VITE_MAX_BOT_USERNAME=$VITE_MAX_BOT_USERNAME
ENV VITE_MINIAPP_URL=$VITE_MINIAPP_URL
COPY package.json ./
RUN npm install --no-audit --no-fund && chmod -R +x node_modules/.bin/
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
