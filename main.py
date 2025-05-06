        # Tables section
        tables_header = QLabel("TABLES")
        tables_header.setObjectName("header_label")
        tables_header.setStyleSheet(get_tables_header_stylesheet())
        left_layout.addWidget(tables_header)
        
        # Tables info label
        tables_info = QLabel("Right-click on tables to profile columns, analyze structure, and discover distributions.")
        tables_info.setWordWrap(True)
        tables_info.setStyleSheet("color: #7FB3D5; font-size: 11px; margin-top: 2px; margin-bottom: 5px;")
        left_layout.addWidget(tables_info)
        
        # Tables list with custom styling
        self.tables_list = DraggableTablesList(self)
        self.tables_list.itemClicked.connect(self.show_table_preview)
        self.tables_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tables_list.customContextMenuRequested.connect(self.show_tables_context_menu)
        left_layout.addWidget(self.tables_list) 