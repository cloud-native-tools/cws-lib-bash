name: deploy-pages

triggers:
  push:

jobs:
  deploy:
    image: __IMAGE__
    steps:
      - uses: checkout
      - id: build-website
        run: |
          if [ -d __DOCS_DIR__ ]; then (cd __DOCS_DIR__ && hugo --minify); fi
          mkdir -p __DOCS_DIR__/public
      - uses: deploy-pages
        inputs:
          deploy-dir: __DOCS_DIR__/public/
          production-branch: __BRANCH__
          site-name: __SITE_NAME__
