FROM node:22-alpine

WORKDIR /repo

COPY package.json package-lock.json /repo/
COPY frontend/package.json /repo/frontend/package.json
RUN npm install

COPY frontend /repo/frontend
WORKDIR /repo/frontend

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
