import pandas as pd
import numpy as np
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
import nltk
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import LatentDirichletAllocation, NMF
from sklearn.cluster import KMeans, DBSCAN
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.manifold import TSNE
from collections import defaultdict, Counter
import re
import warnings
warnings.filterwarnings('ignore')

# Optional imports with fallbacks
try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    print("Note: spaCy not available. Install with: python -m pip install spacy && python -m spacy download en_core_web_sm")

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')
try:
    nltk.data.find('tokenizers/punkt_tab/english')
except LookupError:
    nltk.download('punkt_tab')

class AdvancedTextAnalyzer:
    """
    Advanced text analyzer using multiple academic algorithms for sophisticated 
    feature extraction and semantic analysis.
    """
    
    def __init__(self, model_name='en_core_web_sm'):
        """
        Initialize the advanced text analyzer.
        
        Args:
            model_name (str): Spacy model name for NER and advanced processing
        """
        self.stop_words = set(stopwords.words('english'))
        self.tfidf_vectorizer = None
        self.lda_model = None
        self.nmf_model = None
        self.word_clusters = None
        self.concept_mapping = {}
        
        # Try to load spaCy model for NER
        if SPACY_AVAILABLE:
            try:
                self.nlp = spacy.load(model_name)
            except OSError:
                print(f"Warning: spaCy model '{model_name}' not found. Install with: python -m spacy download {model_name}")
                self.nlp = None
        else:
            self.nlp = None
    
    def extract_semantic_concepts(self, texts, n_topics=8, min_concept_freq=2):
        """
        Extract semantic concepts using multiple algorithms:
        1. Topic Modeling (LDA + NMF)
        2. TF-IDF with clustering
        3. Named Entity Recognition (if available)
        4. N-gram concept extraction
        
        Args:
            texts (list): List of text documents
            n_topics (int): Number of topics for topic modeling
            min_concept_freq (int): Minimum frequency for concept inclusion
            
        Returns:
            dict: Dictionary mapping concept types to extracted concepts
        """
        concepts = {
            'topics_lda': [],
            'topics_nmf': [],
            'entities': [],
            'semantic_clusters': [],
            'key_ngrams': [],
            'domain_concepts': []
        }
        
        if not texts or len(texts) == 0:
            return concepts
        
        # Clean and preprocess texts
        cleaned_texts = [self._preprocess_text(text) for text in texts if isinstance(text, str)]
        if not cleaned_texts:
            return concepts
        
        # 1. Topic Modeling with LDA and NMF
        concepts['topics_lda'] = self._extract_topics_lda(cleaned_texts, n_topics)
        concepts['topics_nmf'] = self._extract_topics_nmf(cleaned_texts, n_topics)
        
        # 2. Named Entity Recognition (if spaCy is available)
        if SPACY_AVAILABLE and self.nlp:
            concepts['entities'] = self._extract_named_entities(texts)
        
        # 3. Semantic clustering of words
        concepts['semantic_clusters'] = self._extract_semantic_clusters(cleaned_texts)
        
        # 4. Key N-gram extraction
        concepts['key_ngrams'] = self._extract_key_ngrams(cleaned_texts, min_concept_freq)
        
        # 5. Domain-specific concept extraction
        concepts['domain_concepts'] = self._extract_domain_concepts(cleaned_texts)
        
        return concepts
    
    def _preprocess_text(self, text):
        """Advanced text preprocessing"""
        if not isinstance(text, str):
            return ""
        
        # Convert to lowercase and remove extra whitespace
        text = re.sub(r'\s+', ' ', text.lower().strip())
        
        # Remove special characters but keep important punctuation
        text = re.sub(r'[^\w\s\-\.]', ' ', text)
        
        # Tokenize
        tokens = word_tokenize(text)
        
        # Remove stopwords and short tokens
        tokens = [token for token in tokens if token not in self.stop_words and len(token) > 2]
        
        return ' '.join(tokens)
    
    def _extract_topics_lda(self, texts, n_topics):
        """Extract topics using Latent Dirichlet Allocation"""
        try:
            # Create TF-IDF vectorizer
            self.tfidf_vectorizer = TfidfVectorizer(
                max_features=1000,
                ngram_range=(1, 3),
                min_df=2,
                max_df=0.8
            )
            
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)
            
            # Apply LDA
            self.lda_model = LatentDirichletAllocation(
                n_components=n_topics,
                random_state=42,
                max_iter=10
            )
            
            self.lda_model.fit(tfidf_matrix)
            
            # Extract topic keywords
            feature_names = self.tfidf_vectorizer.get_feature_names_out()
            topics = []
            
            for topic_idx, topic in enumerate(self.lda_model.components_):
                top_words = [feature_names[i] for i in topic.argsort()[-5:][::-1]]
                topic_name = f"topic_lda_{topic_idx}_{'_'.join(top_words[:2])}"
                topics.append({
                    'name': topic_name,
                    'keywords': top_words,
                    'weight': float(np.sum(topic))
                })
            
            return topics
            
        except Exception as e:
            print(f"LDA topic extraction failed: {e}")
            return []
    
    def _extract_topics_nmf(self, texts, n_topics):
        """Extract topics using Non-negative Matrix Factorization"""
        try:
            if self.tfidf_vectorizer is None:
                self.tfidf_vectorizer = TfidfVectorizer(
                    max_features=1000,
                    ngram_range=(1, 3),
                    min_df=2,
                    max_df=0.8
                )
                tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)
            else:
                tfidf_matrix = self.tfidf_vectorizer.transform(texts)
            
            # Apply NMF
            self.nmf_model = NMF(
                n_components=n_topics,
                random_state=42,
                alpha_W=0.1,
                alpha_H=0.1
            )
            
            self.nmf_model.fit(tfidf_matrix)
            
            # Extract topic keywords
            feature_names = self.tfidf_vectorizer.get_feature_names_out()
            topics = []
            
            for topic_idx, topic in enumerate(self.nmf_model.components_):
                top_words = [feature_names[i] for i in topic.argsort()[-5:][::-1]]
                topic_name = f"topic_nmf_{topic_idx}_{'_'.join(top_words[:2])}"
                topics.append({
                    'name': topic_name,
                    'keywords': top_words,
                    'weight': float(np.sum(topic))
                })
            
            return topics
            
        except Exception as e:
            print(f"NMF topic extraction failed: {e}")
            return []
    
    def _extract_named_entities(self, texts):
        """Extract named entities using spaCy"""
        if self.nlp is None:
            return []
        
        entities = defaultdict(list)
        
        try:
            for text in texts:
                if isinstance(text, str):
                    doc = self.nlp(text)
                    for ent in doc.ents:
                        # Focus on relevant entity types
                        if ent.label_ in ['ORG', 'PRODUCT', 'TECHNOLOGY', 'EVENT', 'GPE', 'PERSON']:
                            entities[ent.label_].append(ent.text.lower())
            
            # Convert to concept format
            entity_concepts = []
            for entity_type, entity_list in entities.items():
                # Get most common entities of each type
                common_entities = Counter(entity_list).most_common(5)
                for entity, count in common_entities:
                    if count >= 2:  # Must appear at least twice
                        entity_concepts.append({
                            'name': f"entity_{entity_type.lower()}_{entity.replace(' ', '_')}",
                            'type': entity_type,
                            'entity': entity,
                            'frequency': count
                        })
            
            return entity_concepts
            
        except Exception as e:
            print(f"Named entity extraction failed: {e}")
            return []
    
    def _extract_semantic_clusters(self, texts):
        """Extract semantic word clusters using TF-IDF and clustering"""
        try:
            if self.tfidf_vectorizer is None:
                self.tfidf_vectorizer = TfidfVectorizer(
                    max_features=500,
                    ngram_range=(1, 2),
                    min_df=2,
                    max_df=0.8
                )
                tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)
            else:
                tfidf_matrix = self.tfidf_vectorizer.transform(texts)
            
            # Get feature names (words/phrases)
            feature_names = self.tfidf_vectorizer.get_feature_names_out()
            
            if len(feature_names) < 5:
                return []
            
            # Cluster words based on their TF-IDF vectors
            n_clusters = min(8, len(feature_names) // 3)
            if n_clusters < 2:
                return []
            
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            
            # Transpose to cluster features (words) instead of documents
            word_clusters = kmeans.fit_predict(tfidf_matrix.T.toarray())
            
            # Group words by cluster
            clusters = defaultdict(list)
            for word_idx, cluster_id in enumerate(word_clusters):
                clusters[cluster_id].append(feature_names[word_idx])
            
            # Convert to concept format
            cluster_concepts = []
            for cluster_id, words in clusters.items():
                if len(words) >= 2:  # Only clusters with multiple words
                    # Sort words by their average TF-IDF score
                    cluster_name = f"semantic_cluster_{cluster_id}_{'_'.join(words[:2])}"
                    cluster_concepts.append({
                        'name': cluster_name,
                        'words': words,
                        'cluster_id': cluster_id,
                        'size': len(words)
                    })
            
            return cluster_concepts
            
        except Exception as e:
            print(f"Semantic clustering failed: {e}")
            return []
    
    def _extract_key_ngrams(self, texts, min_freq=2):
        """Extract key n-grams using advanced scoring"""
        try:
            # Extract 2-grams and 3-grams
            ngram_vectorizer = TfidfVectorizer(
                ngram_range=(2, 3),
                min_df=min_freq,
                max_df=0.8,
                stop_words='english'
            )
            
            ngram_matrix = ngram_vectorizer.fit_transform(texts)
            feature_names = ngram_vectorizer.get_feature_names_out()
            
            # Calculate importance scores
            tfidf_scores = np.array(ngram_matrix.sum(axis=0)).flatten()
            
            # Get top n-grams
            top_indices = tfidf_scores.argsort()[-15:][::-1]
            
            ngram_concepts = []
            for idx in top_indices:
                if tfidf_scores[idx] > 0:
                    ngram = feature_names[idx]
                    ngram_concepts.append({
                        'name': f"ngram_{ngram.replace(' ', '_')}",
                        'ngram': ngram,
                        'score': float(tfidf_scores[idx])
                    })
            
            return ngram_concepts
            
        except Exception as e:
            print(f"N-gram extraction failed: {e}")
            return []
    
    def _extract_domain_concepts(self, texts):
        """Extract domain-specific concepts using keyword patterns"""
        # Define domain-specific patterns
        domain_patterns = {
            'ai_ml': [
                r'\b(artificial intelligence|ai|machine learning|ml|deep learning|neural network|nlp|computer vision|data science)\b',
                r'\b(algorithm|model|training|prediction|classification|regression|clustering)\b',
                r'\b(tensorflow|pytorch|scikit|keras|pandas|numpy)\b'
            ],
            'tech': [
                r'\b(software|hardware|system|platform|framework|database|api|cloud|server)\b',
                r'\b(programming|development|coding|bug|feature|deployment|testing)\b',
                r'\b(python|java|javascript|sql|html|css|react|node)\b'
            ],
            'business': [
                r'\b(revenue|profit|sales|customer|market|strategy|growth|roi|kpi)\b',
                r'\b(management|team|project|budget|timeline|milestone|deliverable)\b',
                r'\b(analytics|metrics|dashboard|report|insight|trend)\b'
            ],
            'academic': [
                r'\b(research|study|analysis|experiment|hypothesis|methodology|results)\b',
                r'\b(publication|paper|journal|conference|peer review|citation)\b',
                r'\b(university|college|professor|student|degree|thesis)\b'
            ]
        }
        
        domain_concepts = []
        combined_text = ' '.join(texts).lower()
        
        for domain, patterns in domain_patterns.items():
            domain_matches = set()
            for pattern in patterns:
                matches = re.findall(pattern, combined_text)
                domain_matches.update(matches)
            
            if domain_matches:
                domain_concepts.append({
                    'name': f"domain_{domain}",
                    'domain': domain,
                    'concepts': list(domain_matches),
                    'count': len(domain_matches)
                })
        
        return domain_concepts


def get_advanced_ohe(dataframe: pd.DataFrame, column: str, 
                    binary_format: str = "numeric",
                    analysis_type: str = "comprehensive",
                    n_topics: int = 6,
                    max_features: int = 25) -> pd.DataFrame:
    """
    Create sophisticated one-hot encoded columns using advanced academic algorithms.
    
    Args:
        dataframe (pd.DataFrame): Input dataframe
        column (str): Name of the column to process
        binary_format (str): Format for encoding - "numeric" for 1/0 or "text" for "Yes"/"No"
        analysis_type (str): Type of analysis - "comprehensive", "topic_focused", "entity_focused", "semantic_focused"
        n_topics (int): Number of topics for topic modeling
        max_features (int): Maximum number of features to create
        
    Returns:
        pd.DataFrame: Original dataframe with additional sophisticated one-hot encoded columns
    """
    # Check if column exists
    if column not in dataframe.columns:
        raise ValueError(f"Column '{column}' not found in dataframe")
    
    # Check binary format is valid
    if binary_format not in ["numeric", "text"]:
        raise ValueError("binary_format must be either 'numeric' or 'text'")
    
    # Filter out non-string values and get text data
    text_data = dataframe[column].dropna().astype(str).tolist()
    if not text_data:
        return dataframe  # Nothing to process
    
    # Initialize advanced analyzer
    analyzer = AdvancedTextAnalyzer()
    
    # Extract sophisticated concepts
    print("Extracting semantic concepts using advanced algorithms...")
    concepts = analyzer.extract_semantic_concepts(text_data, n_topics=n_topics)
    
    # Create features based on analysis type
    features_to_create = []
    
    if analysis_type in ["comprehensive", "topic_focused"]:
        # Add topic-based features
        for topic in concepts['topics_lda']:
            features_to_create.append({
                'name': f"has_{topic['name']}",
                'type': 'topic_lda',
                'keywords': topic['keywords']
            })
        
        for topic in concepts['topics_nmf']:
            features_to_create.append({
                'name': f"has_{topic['name']}",
                'type': 'topic_nmf',
                'keywords': topic['keywords']
            })
    
    if analysis_type in ["comprehensive", "entity_focused"]:
        # Add entity-based features
        for entity in concepts['entities']:
            features_to_create.append({
                'name': f"has_{entity['name']}",
                'type': 'entity',
                'entity_text': entity['entity']
            })
    
    if analysis_type in ["comprehensive", "semantic_focused"]:
        # Add semantic cluster features
        for cluster in concepts['semantic_clusters']:
            features_to_create.append({
                'name': f"has_{cluster['name']}",
                'type': 'semantic_cluster',
                'words': cluster['words']
            })
        
        # Add n-gram features
        for ngram in concepts['key_ngrams'][:10]:  # Top 10 n-grams
            features_to_create.append({
                'name': f"has_{ngram['name']}",
                'type': 'ngram',
                'ngram_text': ngram['ngram']
            })
    
    if analysis_type == "comprehensive":
        # Add domain concept features
        for domain in concepts['domain_concepts']:
            features_to_create.append({
                'name': f"has_{domain['name']}",
                'type': 'domain',
                'domain_concepts': domain['concepts']
            })
    
    # Limit features to max_features
    features_to_create = features_to_create[:max_features]
    
    # Create the actual features
    print(f"Creating {len(features_to_create)} sophisticated features...")
    
    for feature in features_to_create:
        column_name = feature['name']
        
        if feature['type'] in ['topic_lda', 'topic_nmf']:
            # Topic-based features: check if any keyword appears in text
            if binary_format == "numeric":
                dataframe[column_name] = dataframe[column].apply(
                    lambda x: 1 if isinstance(x, str) and any(keyword in str(x).lower() for keyword in feature['keywords']) else 0
                )
            else:
                dataframe[column_name] = dataframe[column].apply(
                    lambda x: "Yes" if isinstance(x, str) and any(keyword in str(x).lower() for keyword in feature['keywords']) else "No"
                )
        
        elif feature['type'] == 'entity':
            # Entity-based features
            if binary_format == "numeric":
                dataframe[column_name] = dataframe[column].apply(
                    lambda x: 1 if isinstance(x, str) and feature['entity_text'] in str(x).lower() else 0
                )
            else:
                dataframe[column_name] = dataframe[column].apply(
                    lambda x: "Yes" if isinstance(x, str) and feature['entity_text'] in str(x).lower() else "No"
                )
        
        elif feature['type'] == 'semantic_cluster':
            # Semantic cluster features
            if binary_format == "numeric":
                dataframe[column_name] = dataframe[column].apply(
                    lambda x: 1 if isinstance(x, str) and any(word in str(x).lower() for word in feature['words']) else 0
                )
            else:
                dataframe[column_name] = dataframe[column].apply(
                    lambda x: "Yes" if isinstance(x, str) and any(word in str(x).lower() for word in feature['words']) else "No"
                )
        
        elif feature['type'] == 'ngram':
            # N-gram features
            if binary_format == "numeric":
                dataframe[column_name] = dataframe[column].apply(
                    lambda x: 1 if isinstance(x, str) and feature['ngram_text'] in str(x).lower() else 0
                )
            else:
                dataframe[column_name] = dataframe[column].apply(
                    lambda x: "Yes" if isinstance(x, str) and feature['ngram_text'] in str(x).lower() else "No"
                )
        
        elif feature['type'] == 'domain':
            # Domain concept features
            if binary_format == "numeric":
                dataframe[column_name] = dataframe[column].apply(
                    lambda x: 1 if isinstance(x, str) and any(concept in str(x).lower() for concept in feature['domain_concepts']) else 0
                )
            else:
                dataframe[column_name] = dataframe[column].apply(
                    lambda x: "Yes" if isinstance(x, str) and any(concept in str(x).lower() for concept in feature['domain_concepts']) else "No"
                )
    
    return dataframe


def analyze_concept_correlations(dataframe: pd.DataFrame, encoded_columns: list) -> dict:
    """
    Analyze correlations between extracted concepts to identify hidden patterns.
    
    Args:
        dataframe (pd.DataFrame): DataFrame with encoded columns
        encoded_columns (list): List of encoded column names
        
    Returns:
        dict: Analysis results including correlation matrix and insights
    """
    if not encoded_columns:
        return {}
    
    # Calculate correlation matrix
    correlation_matrix = dataframe[encoded_columns].corr()
    
    # Find strong correlations (> 0.5)
    strong_correlations = []
    for i, col1 in enumerate(encoded_columns):
        for j, col2 in enumerate(encoded_columns[i+1:], i+1):
            corr_value = correlation_matrix.loc[col1, col2]
            if abs(corr_value) > 0.5:
                strong_correlations.append({
                    'feature1': col1,
                    'feature2': col2,
                    'correlation': corr_value,
                    'strength': 'strong' if abs(corr_value) > 0.7 else 'moderate'
                })
    
    # Analyze concept co-occurrence patterns
    co_occurrence_patterns = []
    for correlation in strong_correlations:
        if correlation['correlation'] > 0.5:  # Positive correlation
            pattern = {
                'pattern_type': 'co_occurrence',
                'features': [correlation['feature1'], correlation['feature2']],
                'strength': correlation['correlation'],
                'interpretation': f"When {correlation['feature1']} is present, {correlation['feature2']} is also likely to be present"
            }
            co_occurrence_patterns.append(pattern)
    
    return {
        'correlation_matrix': correlation_matrix,
        'strong_correlations': strong_correlations,
        'co_occurrence_patterns': co_occurrence_patterns,
        'summary': {
            'total_features': len(encoded_columns),
            'strong_correlations_count': len([c for c in strong_correlations if c['strength'] == 'strong']),
            'moderate_correlations_count': len([c for c in strong_correlations if c['strength'] == 'moderate'])
        }
    }


def test_advanced_ohe():
    """Test the advanced OHE function with AI/ML related text"""
    print("\n===== Testing Advanced OHE with AI/ML Text =====")
    
    # Create sample data with AI/ML related text
    ai_texts = [
        "Developing machine learning models using TensorFlow and neural networks for computer vision tasks",
        "Implementing deep learning algorithms for natural language processing and text classification",
        "Using artificial intelligence to automate data science workflows and predictive analytics",
        "Building recommendation systems with collaborative filtering and matrix factorization techniques",
        "Applying reinforcement learning agents to optimize decision making in complex environments",
        "Creating chatbots using large language models and transformer architectures like BERT",
        "Deploying ML models to production using Docker containers and Kubernetes orchestration",
        "Analyzing big data with Apache Spark and implementing real-time streaming analytics",
        "Using computer vision for object detection and image segmentation in autonomous vehicles",
        "Implementing explainable AI techniques to understand model predictions and bias detection"
    ]
    
    # Create dataframe
    df = pd.DataFrame({'ai_description': ai_texts})
    
    print("Original DataFrame:")
    print(df)
    
    # Test comprehensive analysis
    print("\n----- Testing Comprehensive Analysis -----")
    result_comprehensive = get_advanced_ohe(
        df.copy(), 
        'ai_description', 
        binary_format="numeric",
        analysis_type="comprehensive",
        n_topics=4,
        max_features=20
    )
    
    # Show new columns
    new_columns = [col for col in result_comprehensive.columns if col.startswith('has_')]
    print(f"\nCreated {len(new_columns)} sophisticated features:")
    for col in new_columns:
        print(f"  - {col}")
    
    print("\nSample of results (first 3 rows, new columns only):")
    print(result_comprehensive[new_columns].head(3))
    
    # Analyze correlations
    print("\n----- Analyzing Concept Correlations -----")
    correlation_analysis = analyze_concept_correlations(result_comprehensive, new_columns)
    
    print(f"Summary: {correlation_analysis['summary']}")
    
    if correlation_analysis['strong_correlations']:
        print("\nStrong correlations found:")
        for corr in correlation_analysis['strong_correlations'][:5]:  # Show top 5
            print(f"  {corr['feature1']} <-> {corr['feature2']}: {corr['correlation']:.3f} ({corr['strength']})")
    
    if correlation_analysis['co_occurrence_patterns']:
        print("\nCo-occurrence patterns:")
        for pattern in correlation_analysis['co_occurrence_patterns'][:3]:  # Show top 3
            print(f"  {pattern['interpretation']}")
    
    print("\nAdvanced OHE test completed successfully!")


if __name__ == "__main__":
    test_advanced_ohe() 