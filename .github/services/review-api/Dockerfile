FROM node:22-alpine
WORKDIR /app
COPY .github/dashboard.json .github/yamaa-studies.json .github/
COPY .github/services/review-api/ .github/services/review-api/
COPY docs/assets/dashboard/package.json docs/assets/dashboard/review-comment.js docs/assets/dashboard/review-drafts.js docs/assets/dashboard/
USER node
EXPOSE 8080
CMD ["node", ".github/services/review-api/server.js"]
