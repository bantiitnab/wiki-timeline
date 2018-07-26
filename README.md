# Unfound Timeline
In this project, I build a timeline utility, we takes in a query and return the timeline of relevant article from wikipedia.

## Project details
It is divided into 3 modules
1.) Gather relavant page and it's lines.
2.) build sentence embedding of all lines.
3.) Pick up date expression from lines and choose top lines.
4.) build Flask app tost host it.

## Tech used
Python
numpy
spacy[optional]

## Installation
Install the requirements from requirement.txt

## Testing
1.) Test flask app in browser and try it.
or
2.) Test from command line using
`
python timeline.py gst --lines 10 --spacy False
`