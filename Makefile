coverage:
	pytest --verbose --cov=edgetest

sphinx:
	cd docs && \
	make -f Makefile clean && \
	make -f Makefile html && \
	cd ..

ghpages:
	git checkout gh-pages && \
	cp -r docs/_build/html/* . && \
	touch .nojekyll && \
	git add -u && \
	git add -A && \
	PRE_COMMIT_ALLOW_NO_CONFIG=1 git commit -m "Updated generated Sphinx documentation"
