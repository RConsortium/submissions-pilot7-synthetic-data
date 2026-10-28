#!/usr/bin/env Rscript

runs <- yamaa::yamaa_project("cdiscpilot01/spec/yamaa/resolved/project.yaml")$run("adam")
runs$save()
