from PyQt6.QtCore import Qt, QRegularExpression
from PyQt6.QtGui import QFont, QColor, QSyntaxHighlighter, QTextCharFormat

class SQLSyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.highlighting_rules = []

        # SQL Keywords
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#0000FF"))  # Blue
        keyword_format.setFontWeight(QFont.Weight.Bold)
        keywords = [
            "\\bSELECT\\b", "\\bFROM\\b", "\\bWHERE\\b", "\\bAND\\b", "\\bOR\\b",
            "\\bINNER\\b", "\\bOUTER\\b", "\\bLEFT\\b", "\\bRIGHT\\b", "\\bJOIN\\b",
            "\\bON\\b", "\\bGROUP\\b", "\\bBY\\b", "\\bHAVING\\b", "\\bORDER\\b",
            "\\bLIMIT\\b", "\\bOFFSET\\b", "\\bUNION\\b", "\\bEXCEPT\\b", "\\bINTERSECT\\b",
            "\\bCREATE\\b", "\\bTABLE\\b", "\\bINDEX\\b", "\\bVIEW\\b", "\\bINSERT\\b",
            "\\bINTO\\b", "\\bVALUES\\b", "\\bUPDATE\\b", "\\bSET\\b", "\\bDELETE\\b",
            "\\bTRUNCATE\\b", "\\bALTER\\b", "\\bADD\\b", "\\bDROP\\b", "\\bCOLUMN\\b",
            "\\bCONSTRAINT\\b", "\\bPRIMARY\\b", "\\bKEY\\b", "\\bFOREIGN\\b", "\\bREFERENCES\\b",
            "\\bUNIQUE\\b", "\\bNOT\\b", "\\bNULL\\b", "\\bIS\\b", "\\bDISTINCT\\b",
            "\\bCASE\\b", "\\bWHEN\\b", "\\bTHEN\\b", "\\bELSE\\b", "\\bEND\\b",
            "\\bAS\\b", "\\bWITH\\b", "\\bBETWEEN\\b", "\\bLIKE\\b", "\\bIN\\b",
            "\\bEXISTS\\b", "\\bALL\\b", "\\bANY\\b", "\\bSOME\\b", "\\bDESC\\b", "\\bASC\\b"
        ]
        for pattern in keywords:
            regex = QRegularExpression(pattern, QRegularExpression.PatternOption.CaseInsensitiveOption)
            self.highlighting_rules.append((regex, keyword_format))

        # Functions
        function_format = QTextCharFormat()
        function_format.setForeground(QColor("#AA00AA"))  # Purple
        functions = [
            "\\bAVG\\b", "\\bCOUNT\\b", "\\bSUM\\b", "\\bMAX\\b", "\\bMIN\\b",
            "\\bCOALESCE\\b", "\\bNVL\\b", "\\bNULLIF\\b", "\\bCAST\\b", "\\bCONVERT\\b",
            "\\bLOWER\\b", "\\bUPPER\\b", "\\bTRIM\\b", "\\bLTRIM\\b", "\\bRTRIM\\b",
            "\\bLENGTH\\b", "\\bSUBSTRING\\b", "\\bREPLACE\\b", "\\bCONCAT\\b",
            "\\bROUND\\b", "\\bFLOOR\\b", "\\bCEIL\\b", "\\bABS\\b", "\\bMOD\\b",
            "\\bCURRENT_DATE\\b", "\\bCURRENT_TIME\\b", "\\bCURRENT_TIMESTAMP\\b",
            "\\bEXTRACT\\b", "\\bDATE_PART\\b", "\\bTO_CHAR\\b", "\\bTO_DATE\\b"
        ]
        for pattern in functions:
            regex = QRegularExpression(pattern, QRegularExpression.PatternOption.CaseInsensitiveOption)
            self.highlighting_rules.append((regex, function_format))

        # Numbers
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#009900"))  # Green
        self.highlighting_rules.append((
            QRegularExpression("\\b[0-9]+\\b"),
            number_format
        ))

        # Single-line string literals
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#CC6600"))  # Orange/Brown
        self.highlighting_rules.append((
            QRegularExpression("'[^']*'"),
            string_format
        ))
        self.highlighting_rules.append((
            QRegularExpression("\"[^\"]*\""),
            string_format
        ))

        # Comments
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#777777"))  # Gray
        comment_format.setFontItalic(True)
        self.highlighting_rules.append((
            QRegularExpression("--[^\n]*"),
            comment_format
        ))
        
        # Multi-line comments
        self.comment_start_expression = QRegularExpression("/\\*")
        self.comment_end_expression = QRegularExpression("\\*/")
        self.multi_line_comment_format = comment_format

    def highlightBlock(self, text):
        # Apply regular expression highlighting rules
        for pattern, format in self.highlighting_rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), format)

        # Handle multi-line comments
        self.setCurrentBlockState(0)
        
        # If previous block was inside a comment, check if this block continues it
        start_index = 0
        if self.previousBlockState() != 1:
            # Find the start of a comment
            start_match = self.comment_start_expression.match(text)
            if start_match.hasMatch():
                start_index = start_match.capturedStart()
            else:
                return
            
        while start_index >= 0:
            # Find the end of the comment
            end_match = self.comment_end_expression.match(text, start_index)
            
            # If end match found
            if end_match.hasMatch():
                end_index = end_match.capturedStart()
                comment_length = end_index - start_index + end_match.capturedLength()
                self.setFormat(start_index, comment_length, self.multi_line_comment_format)
                
                # Look for next comment
                start_match = self.comment_start_expression.match(text, start_index + comment_length)
                if start_match.hasMatch():
                    start_index = start_match.capturedStart()
                else:
                    start_index = -1
            else:
                # No end found, comment continues to next block
                self.setCurrentBlockState(1)  # Still inside comment
                comment_length = len(text) - start_index
                self.setFormat(start_index, comment_length, self.multi_line_comment_format)
                start_index = -1 