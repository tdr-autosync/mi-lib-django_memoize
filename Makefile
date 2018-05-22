pypi:
	python setup.py sdist 
	twine upload dist/*
	python setup.py build_sphinx
