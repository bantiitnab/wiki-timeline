import requests
import re
import bs4
import copy
import argparse
from datetime import datetime

from .sentence_embedding import timeline_sentences_embeddings
from .datefinder import DateFinder

class Timeline(object):

    QUERY_EXCLUDES = ['File:', 'Help:', 'Special:PrefixIndex']                
    WIKI_BASE_URL = 'https://en.wikipedia.org/wiki/'
    BASE_DATE = datetime(1000,1,1)
    GLOVE_FILE_PATH = './glove.6B/glove.6B.50d.txt'

    def __init__(self, use_spacy=False, embeddings=False):
        self.date_finder = DateFinder(base_date=self.BASE_DATE, use_spacy=use_spacy)        
        self.today = datetime.now()
        self.embeddings = embeddings


    def get_wiki_pages_query(self, query):
        """
            returns all possible queries for particular 'query'
            or None if nothing there
            e.g. for gst, we get [gst_india, gst_usa, etc]
        """

        # get response from wiki page    
        try:           
            response = requests.get(self.WIKI_BASE_URL + query)        
        except Exception as e:
            print('Connection error, sending default query')
            return ['gst']

        # we use bs4 for understanding html and pick main content
        soup = bs4.BeautifulSoup(response.text, 'html.parser')        
        content = soup.find(id='mw-content-text')
        
        # if we find no page, we return None
        # if query got directed to actual page, we would return this page 
        # else we would list of queries directing to actual pages
        if soup.find(id='noarticletext'):
            print('Failed to find any relevant page')
            return None

        if soup.find(id='References'):
            return [query]
        else:
            links = content.find_all('a')
            queries = []
            # pattern to extract query from links
            query_pat = re.compile('/wiki/([^\"]+)')
            for link in links:    
                match = re.search(query_pat, link['href'])
                if match:
                    query_match = match.group(1)
                    # exclude some queries
                    add_query = True
                    for exclude in self.QUERY_EXCLUDES:
                        if exclude in query_match:
                            add_query = False
                            break       
                            
                    if add_query:
                        queries.append(query_match)
            return queries  


    def get_page_lines(self, query): 
        """
            breaks page text into lines and returns it            
        """  

        # get response
        try:            
            response = requests.get(self.WIKI_BASE_URL + query).text
        except Exception as e:
            print('Connection error, using default response')
            response = open('/Users/akhilesh/Desktop/st.htm', 'r').read()
        
        # build soup and get desired content
        soup = bs4.BeautifulSoup(response, 'html.parser')    
        main_content = soup.find(class_='mw-parser-output')
        
        # pick up the text in form of lines    
        node = main_content.contents[0]
        lines = []    
        while node is not None:
            if not isinstance(node, bs4.NavigableString):
                # stop here
                if node.find(id='References'):
                    print('Extracting lines stopped...')
                    break
                    
                # replace [43] kind of references
                para = re.sub('\[\d+\]', '', node.text)
                # split para into lines
                para_lines = re.split('(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', para)
                lines.append(para_lines)
            node = node.next_sibling            
            
        return lines
    

    def get_clean_timeline(self, timeline):
        """
            clean the dates in line, like date from future or dates before base_date
        """
        
        # dont include lines with 
        # year less than  1000, year same as base_date year, 
        timeline_clone = []
        for event in timeline:                        
            line = event[0]
            dates = event[1]
            dates_clone = []
            for date in dates:                  
                if date[0].year <= self.BASE_DATE.year or \
                    date[0].year > self.today.year:
                    continue
                dates_clone.append(date)            
            if dates_clone:
                timeline_clone.append([line, dates_clone, event[2]])

        # sort timeline on base of first date of sentence
        timeline_clone.sort(key=lambda x: x[1][0][0])
        return timeline_clone


    def pickup_top_events(self, timeline, timeline_len=None):
        """
            return top events from timeline, right now using 2 filters
        """

        # pickup events from different year if more events than asked
        # right now using first date from each sentence as decider
        timeline_by_year = []
        if len(timeline) > timeline_len:
            years_picked = []
            for event in timeline:
                line = event[0]
                dates = event[1]
                year = dates[0][0].year
                if year not in years_picked:
                    timeline_by_year.append([line, dates, event[2]])
                years_picked.append(year)
        else:
            timeline_by_year = copy.copy(timeline)
        
        
        if len(timeline_by_year) > timeline_len:
            # pickup 50 % recent and 50 % from others    
            x = len(timeline_by_year) - int(timeline_len / 2)
            if timeline_len % 2 == 1:
                x = max(x - 1, 0)
            step = int(x / int(timeline_len / 2))
            top_indices = list(range(0, x - 1, step)) + \
                            list(range( x, len(timeline_by_year)))  
        else:
            top_indices = list(range(0, len(timeline_by_year)))              
        # slice indices again
        top_indices = top_indices[-timeline_len:]

        top_timeline = []
        for i in top_indices:
            top_timeline.append(timeline_by_year[i])
        
        return top_timeline


    def build_timeline(self, query, timeline_len=5, use_spacy=False, embeddings=True):
        """
        main function for building timeline
        returns: 
            [
            [line1, [(datetime1, date1_string), (datetime2, date2_string)]],
            [line1, [(datetime1, date1_string)]]
            ...
            ]
        """

        # get wiki pages possible queries
        # if we landed on index page, we will pick send back all other
        # possible wiki pages query
        wiki_pages_query = self.get_wiki_pages_query(query)

        if not wiki_pages_query:
            return None, None
        
        # get lines of first query        
        wiki_page_query = wiki_pages_query[0]
        print('Building timeline for {}'.format(wiki_page_query))

        lines = self.get_page_lines(wiki_page_query)                   
        if lines is None:
           print('Invalid query')
           return None
        
        # build the timeline
        timeline = []        
        for para_lines in lines:
            for line in para_lines:                
                if use_spacy is True:                    
                    matches = self.date_finder.find_dates_with_spacy(line, source=True)    
                else:                       
                    matches = list(self.date_finder.find_dates(line, source=True, strict=True))                
                if matches:
                    # print(line, matches)
                    timeline.append([line, matches])

        # get embeddings of all lines using the article text
        timeline = timeline_sentences_embeddings(timeline, glove_file_path=self.GLOVE_FILE_PATH)
        
        # clean timeline        
        timeline = self.get_clean_timeline(timeline)
        # print('all timeline ----', len(timeline))
        # for d in timeline:
        #     print(d)

        # pickup top events from timeline
        timeline = self.pickup_top_events(timeline, timeline_len)        
        # print('top timeline ----- ', len(timeline))
        # for d in timeline:
        #     print(d)

        return timeline, wiki_pages_query


def get_timeline(query, timeline_len=5, use_spacy=False, embeddings=True):        
    timeline = Timeline(use_spacy=use_spacy, embeddings=embeddings)
    return timeline.build_timeline(query, timeline_len=timeline_len, use_spacy=use_spacy, embeddings=embeddings)


def main():
    # load options from commandline
    parser = argparse.ArgumentParser()        
    parser.add_argument('query', default='gst')
    parser.add_argument('--lines', type=int, default=5)
    parser.add_argument('--spacy', default='False')
    parser.add_argument('--embeddings', default='True')
    parser.add_argument('--glove_path', default='static/glove.6B/glove.6B.50d.txt')    

    args = parser.parse_args()    
    query = args.query
    timeline_len = args.lines
    use_spacy = args.spacy == 'True'
    embeddings = args.embeddings == 'True'
    
    print('use spacy ', use_spacy, type(use_spacy), 'timeline_len', timeline_len)
    print('get embeddings ', embeddings)

    # get timeline valus
    timeline, wiki_pages_query = get_timeline(
                                    query, 
                                    timeline_len=timeline_len,
                                    use_spacy=use_spacy,
                                    embeddings=embeddings
                                )
    print(timeline)


if __name__ == '__main__':     
    main()
    