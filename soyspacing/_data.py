from collections import defaultdict
import pickle
import sys

def normalize_text(raw_fname, normalized_fname, english=False, number=False):
    with open(raw_fname, encoding='utf-8') as fi:
        with open(normalized_fname, 'w', encoding='utf-8') as fo:
            for sent in fi:
                sent = normalize(sent, english, number)
                if not sent:
                    continue
                fo.write('%s\n' % sent)
                
def convert_to_corpus(text_fname, corpus_fname):
    with open(text_fname, encoding='utf-8') as fi:
        with open(corpus_fname, 'w', encoding='utf-8') as fo:
            for sent in fi:
                sent = sent.strip()
                chars, tags = sent_to_chartags(sent)
                tagged_sent = ' '.join(['%s/%d' % (c,t) for c,t in zip(chars, tags)])
                fo.write('%s\n' % tagged_sent)
    
def convert_to_text(corpus_fname, text_fname):
    def tokenize(chartag):
        return chartag.split('/')
    
    with open(corpus_fname, encoding='utf-8') as fi:
        with open(text_fname, 'w', encoding='utf-8') as fo:
            for sent in fi:
                chartags = sent.strip().split()
                chartags = [tokenize(ct) for ct in chartags]
                chars, tags = zip(*chartags)
                spaced_sent = spacing(chars, tags)
                fo.write('%s\n' % spaced_sent)

def spacing(chars, tags, space='1'):
    return ''.join(['%s '%c if t == space else c for c, t in zip(chars, tags)]).strip()

def sent_to_chartags(sent, nonspace=0, space=1):
    chars = sent.replace(' ','')
    tags = [nonspace]*(len(chars) - 1) + [1]
    idx = 0

    for c in sent:
        if c == ' ':
            tags[idx-1] = space
        else:
            idx += 1
    return chars, tags

class FeatureManager:
    
    def __init__(self, template_range_begin=-2, template_range_end=2, min_count=10):
        self.template_range_begin = template_range_begin
        self.template_range_end = template_range_end
        self.min_count = min_count
        self.feature_set = None
        self.templates = self._generate_token_templates(template_range_begin, 
                                                        template_range_end)

    def _generate_token_templates(self, begin=-2, end=2):
        templates = []
        for b in range(begin, end):
            for e in range(b, end+1):
                if (b == 0) or (e == 0):
                    continue
                templates.append((b, e))
        return templates
    
    def scan_features(self, corpus):
        counter = defaultdict(lambda: 0)
        for n_sent, sent in enumerate(corpus):
            if n_sent % 1000 == 0:
                args = ((n_sent+1)/len(corpus), '%', n_sent+1, len(corpus))
                sys.stdout.write('\rscanning features ... %.3f %s (%d in %d)' % args)
                
            features = self.sent_to_features(sent)
            for feature in features:
                counter[feature] += 1
                
        self.feature_set = {feature for feature, count in counter.items() if count >= self.min_count}
        args = (len(self.feature_set), self.min_count)
        print('\rscanning features was done. num features = %d (min_count = %d)' % args)

    def sent_to_features(self, sent):
        def to_feature(sent):
            x =[]
            for i in range(len(sent)):
                xi = []
                e_max = len(sent)
                for t in self.templates:
                    b = i + t[0]
                    e = i + t[1] + 1
                    if b < 0 or e > e_max:
                        continue
                    if b == (e - 1):
                        xi.append(('X[%d]' % t[0], sent[b]))
                    else:
                        contexts = sent[b:e] if t[0] * t[1] > 0 else sent[b:i] + sent[i+1:e]        
                        xi.append(('X[%d,%d]' % (t[0], t[1]), tuple(contexts)))
                x.append(xi)
            return x

        x = to_feature(sent)
        if self.feature_set:
            x = [[f for f in xi if f in self.feature_set] for xi in x]
        return x
    
    def save(self, fname):
        with open(fname, 'wb') as f:
            params = {
                'range_begin': self.template_range_begin,
                'range_end': self.template_range_end,
                'min_count': self.min_count,
                'feature_set': self.feature_set,
                'templates': self.templates
            }
            pickle.dump(params, f)
        
    def load(self, fname):
        with open(fname, 'rb') as f:
            params = pickle.load(f)
            self.template_range_begin = params['range_begin']
            self.template_range_end = params['range_end']
            self.min_count = params['min_count']
            self.feature_set = params['feature_set']
            self.templates = params['templates']

class Corpus:
    
    def __init__(self, corpus_fname):
        self.corpus_fname = corpus_fname
        self.length = 0
    
    def __iter__(self):
        with open(self.fname, encoding='utf-8') as f:
            for sent in f:
                yield sent_to_chartags(sent, nonspace=0, space=1)
                
    def __len__(self):
        if self.length == 0:
            with open(self.fname, encoding='utf-8') as f:
                for n_sent, _ in enumerate(f):
                    continue
                self.length = (n_sent + 1)
        return self.length
    
class FeaturizedCorpus(Corpus):
    
    def __init__(self, corpus_fname, feature_manager):
        super().__init__(corpus_fname)
        self.feature_manager = feature_manager
        
    def __iter__(self):
        with open(self.fname, encoding='utf-8') as f:
            for sent in f:
                sent = sent_to_chartags(sent, nonspace=0, space=1)
                yield self.feature_manager.sent_to_features(sent)