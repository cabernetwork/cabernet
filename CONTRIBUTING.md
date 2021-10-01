Hello all.  For those of you who wish to contribute code, here's a few things to 
take note of:

## Project Goal
To allow Locast to be used in Plex (and possibly other media servers), for the 
express purpose of serving those who want another way to access broadcast TV in 
their service area.  We will aim to be a good steward of the Locast terms of service.

## Coding style/linting
For the most part we lint against PEP 8 and pyflakes, with exceptions
for rules E303, E501, W504, W605.  I will be pretty lenient in taking pull requests, 
so don't worry if you're not already familiar with linting.  A good primer
on [linting in Python is here](https://realpython.com/python-code-quality/)'

Aligning with the PEP 8, we use the following naming formats:
 - Classnames: CapWords
 - Methods/Properties: snake_case
 - File names/Package names: snake_case
 - Function/Variable Names: snake_case


## Versioning Scheme
We use the Semantic versioning scheme, with the following naming conventions for non-stable 
releases:
 - The 0.x series is beta
 - Releases marked `-alpha` or `-beta` at the end of the version number. An additional number,
   starting from 1, is added after this postfix to separate different version numbers. 
   Example: `2.0.0-beta3`

## Road Map and New feature discussion
Plans for close-at-hand future releases are typically listed in CHANGELOG. New features 
discussions can be made in GitHub as a new issue.  I can also look into setting up other 
channels of communications to discuss road maps, etc. as well if there is a need.