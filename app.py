from flask import Flask, render_template, request
from timeline.timeline import get_timeline

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'GET':
        return render_template('app.html')
    else:        
        # pick up variables
        query = request.form['query']
        try:        
            lines = int(request.form['lines'])
        except Exception:
            lines = 10        
        if 'spacy' in request.form:
            use_spacy = True
        else:
            use_spacy = False        
        print(query, lines, use_spacy)

        timeline, wiki_pages_query = get_timeline(
                                        query, 
                                        timeline_len=lines, 
                                        use_spacy=use_spacy, 
                                        embeddings=True
                                    )   

        # pickup the first date of that line        
        if timeline:
            timeline = [[event[0], event[1][0][0], list(event[2])] for event in timeline]    
        else:
            timeline = 'invalid'
        return render_template('app.html', **{'timeline': timeline, 'wiki_pages_query': wiki_pages_query})        

if __name__ == '__main__':
    app.run(debug=True, use_reloader=True)