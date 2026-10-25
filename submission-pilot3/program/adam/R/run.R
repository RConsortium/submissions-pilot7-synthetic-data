#!/usr/bin/env Rscript

runs <- yamaa::yamaa_project("submission-pilot3/spec/yamaa/project.yaml")$run("adam")
runs$save()
