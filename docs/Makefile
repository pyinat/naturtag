# Minimal makefile for Sphinx documentation
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = .
AUTOSOURCEDIR = $(SOURCEDIR)/modules
PACKAGEDIR    = ../naturtag
BUILDDIR      = _build



# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help all apidoc clean-apidoc Makefile

all: clean clean-apidoc apidoc html

clean-apidoc:
	rm -rf "$(AUTOSOURCEDIR)"

apidoc:
	sphinx-apidoc -f --no-toc --module-first -o "$(AUTOSOURCEDIR)" "$(PACKAGEDIR)"


# Catch-all target: route all unknown targets to Sphinx
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
