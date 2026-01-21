import 'package:flutter/material.dart';
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;
import 'package:printing/printing.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter/services.dart';

class BookGeneration extends StatefulWidget {
  final VoidCallback onToggleTheme;
  final String backendUrl;

  const BookGeneration({
    super.key,
    required this.onToggleTheme,
    required this.backendUrl,
  });

  @override
  State<BookGeneration> createState() => _BookGenerationState();
}

class _BookGenerationState extends State<BookGeneration>
    with TickerProviderStateMixin {
  // Form controllers
  final TextEditingController _titleController = TextEditingController();
  final TextEditingController _descriptionController = TextEditingController();
  final TextEditingController _topicsController = TextEditingController();

  // Form state
  String _selectedField = 'General Education';
  String _selectedBookType = 'Textbook';

  // Generation state
  bool _isGenerating = false;
  double _generationProgress = 0.0;
  String _currentStep = '';
  List<String> _generatedChapters = [];
  List<String> _topicsList = [];
  late AnimationController _animationController;
  late Animation<double> _progressAnimation;
  bool _showDownloadButton = false;
  bool _fontsLoaded = false;

  // Backend book tracking
  String? _generatedBookId;
  String? _generatedFilename;

  // Field configurations
  final Map<String, Map<String, dynamic>> _fieldConfigs = {
    'Computer Science': {'color': Colors.blue, 'icon': Icons.computer},
    'Mathematics': {'color': Colors.red, 'icon': Icons.calculate},
    'Science': {'color': Colors.green, 'icon': Icons.science},
    'History': {'color': Colors.amber, 'icon': Icons.history},
    'Literature': {'color': Colors.purple, 'icon': Icons.book},
    'Art & Design': {'color': Colors.pink, 'icon': Icons.palette},
    'General Education': {'color': Colors.indigo, 'icon': Icons.school},
  };

  // Book type configurations
  final Map<String, Map<String, dynamic>> _bookTypeConfigs = {
    'Textbook': {'icon': Icons.menu_book},
    'Exam-prep Notes': {'icon': Icons.assignment},
    'Story-style Guide': {'icon': Icons.spa},
    'Research Manual': {'icon': Icons.analytics},
    'Beginner\'s Handbook': {'icon': Icons.import_contacts},
  };

  @override
  void initState() {
    super.initState();
    _animationController = AnimationController(
      duration: const Duration(seconds: 2),
      vsync: this,
    )..repeat(reverse: true);

    _progressAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _animationController, curve: Curves.easeInOut),
    );

    // Load custom fonts (optional now since PDF is generated in backend)
    _loadCustomFonts();
  }

  Future<void> _loadCustomFonts() async {
    // Not needed for PDF generation since it's done in backend
    setState(() {
      _fontsLoaded = true;
    });
  }

  @override
  void dispose() {
    _animationController.dispose();
    _titleController.dispose();
    _descriptionController.dispose();
    _topicsController.dispose();
    super.dispose();
  }

  Future<void> _generateBook() async {
    if (_titleController.text.isEmpty || _topicsController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please fill in all required fields')),
      );
      return;
    }

    setState(() {
      _isGenerating = true;
      _generationProgress = 0.0;
      _generatedChapters.clear();
      _topicsList = _topicsController.text
          .split('\n')
          .where((t) => t.trim().isNotEmpty)
          .toList();
      _showDownloadButton = false;
      _generatedBookId = null;
      _generatedFilename = null;
    });

    try {
      setState(() {
        _currentStep = 'Generating book content...';
      });

      // Call backend to generate complete book with PDF
      final response = await http.post(
        Uri.parse('${widget.backendUrl}/api/generate-book-pdf'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'topics': _topicsList,
          'book_type': _selectedBookType,
          'field': _selectedField,
          'book_name': _titleController.text,
          'book_description': _descriptionController.text,
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);

        if (data['success'] == true) {
          // Get book ID and filename from backend
          final bookId = data['book_id'] as String;
          final filename = data['filename'] as String;
          final chapters = data['book_info']['total_chapters'] as int;

          // Store chapters for display
          if (data['chapters'] != null) {
            final chaptersList = data['chapters'] as List;
            _generatedChapters = chaptersList
                .map((c) => c['content'] as String)
                .toList();
          }

          setState(() {
            _generatedBookId = bookId;
            _generatedFilename = filename;
            _isGenerating = false;
            _currentStep = 'Book generation complete!';
            _showDownloadButton = true;
          });

          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(
                'Generated $chapters chapters successfully! Book is ready for download.',
              ),
              backgroundColor: Colors.green,
            ),
          );
        } else {
          throw Exception(data['error'] ?? 'Unknown error');
        }
      } else {
        throw Exception('HTTP ${response.statusCode}');
      }
    } catch (e) {
      setState(() {
        _isGenerating = false;
        _currentStep = 'Error generating book';
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Error: ${e.toString()}'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  Future<void> _downloadBook() async {
    if (_generatedBookId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No book available to download')),
      );
      return;
    }

    try {
      // Create download URL
      final downloadUrl =
          '${widget.backendUrl}/api/download-book/$_generatedBookId';

      // Open the download URL in browser (this will trigger download)

      // For now, show a dialog with download link
      showDialog(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Download Book'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Book: ${_titleController.text}'),
              const SizedBox(height: 10),
              const Text('Click the link below to download your book:'),
              const SizedBox(height: 10),
              GestureDetector(
                onTap: () {
                  // In web, this will open in new tab
                  // In mobile, need to use url_launcher package
                  Clipboard.setData(ClipboardData(text: downloadUrl));
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text('Download link copied to clipboard'),
                    ),
                  );
                  Navigator.pop(context);
                },
                child: Text(
                  downloadUrl,
                  style: const TextStyle(
                    color: Colors.blue,
                    decoration: TextDecoration.underline,
                  ),
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Close'),
            ),
          ],
        ),
      );
    } catch (e) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Error downloading book: $e')));
    }
  }

  Future<void> _previewBook() async {
    if (_generatedBookId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No book available to preview')),
      );
      return;
    }

    try {
      //For preview, download the PDF and show it
      final downloadUrl =
          '${widget.backendUrl}/api/download-book/$_generatedBookId';

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: const Text('Opening book preview...'),
          action: SnackBarAction(
            label: 'Download',
            onPressed: () => _downloadBook(),
          ),
        ),
      );
      // In web: will download directly
      // In mobile: might need special handling
    } catch (e) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Error previewing book: $e')));
    }
  }

  void _resetForm() {
    setState(() {
      _titleController.clear();
      _descriptionController.clear();
      _topicsController.clear();
      _selectedField = 'General Education';
      _selectedBookType = 'Textbook';
      _isGenerating = false;
      _generationProgress = 0.0;
      _generatedChapters.clear();
      _generatedBookId = null;
      _generatedFilename = null;
      _topicsList.clear();
      _showDownloadButton = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Kiddo Book AI'),
        backgroundColor: Colors.orange.shade700,
        actions: [
          IconButton(
            onPressed: widget.onToggleTheme,
            icon: Icon(
              isDark ? Icons.light_mode : Icons.dark_mode,
              color: Colors.white,
            ),
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: Padding(
              padding: const EdgeInsets.all(20.0),
              child: _isGenerating
                  ? _buildGenerationScreen()
                  : _buildInputScreen(),
            ),
          ),
          if (_showDownloadButton && _generatedBookId != null) ...[
            Container(
              color: isDark ? Colors.grey.shade900 : Colors.grey.shade50,
              padding: const EdgeInsets.all(20.0),
              child: Column(
                children: [
                  Text(
                    'Your Book is Ready!',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: isDark ? Colors.white : Colors.black,
                    ),
                  ),
                  const SizedBox(height: 10),
                  Text(
                    'Download your generated book or create a new one:',
                    style: TextStyle(
                      color: isDark
                          ? Colors.grey.shade400
                          : Colors.grey.shade600,
                    ),
                  ),
                  const SizedBox(height: 15),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                    children: [
                      ElevatedButton.icon(
                        onPressed: _previewBook,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.blue.shade700,
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(
                            vertical: 15,
                            horizontal: 20,
                          ),
                        ),
                        icon: const Icon(Icons.preview),
                        label: const Text('Preview'),
                      ),
                      ElevatedButton.icon(
                        onPressed: _downloadBook,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.green.shade700,
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(
                            vertical: 15,
                            horizontal: 20,
                          ),
                        ),
                        icon: const Icon(Icons.download),
                        label: const Text('Download'),
                      ),
                      ElevatedButton.icon(
                        onPressed: _resetForm,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: isDark
                              ? Colors.grey.shade700
                              : Colors.grey.shade300,
                          foregroundColor: isDark ? Colors.white : Colors.black,
                          padding: const EdgeInsets.symmetric(
                            vertical: 15,
                            horizontal: 20,
                          ),
                        ),
                        icon: const Icon(Icons.refresh),
                        label: const Text('New Book'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildInputScreen() {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TextField(
            controller: _titleController,
            style: TextStyle(color: isDark ? Colors.white : Colors.black),
            decoration: InputDecoration(
              labelText: 'Book Title *',
              labelStyle: TextStyle(
                color: isDark ? Colors.grey.shade400 : null,
              ),
              hintText: 'Enter your book title',
              hintStyle: TextStyle(color: isDark ? Colors.grey.shade500 : null),
              border: const OutlineInputBorder(),
              prefixIcon: Icon(
                Icons.title,
                color: isDark ? Colors.grey.shade400 : null,
              ),
              enabledBorder: OutlineInputBorder(
                borderSide: BorderSide(
                  color: isDark ? Colors.grey.shade700 : Colors.grey.shade400,
                ),
              ),
              focusedBorder: OutlineInputBorder(
                borderSide: BorderSide(color: Colors.orange.shade700),
              ),
            ),
          ),
          const SizedBox(height: 20),
          TextField(
            controller: _descriptionController,
            style: TextStyle(color: isDark ? Colors.white : Colors.black),
            maxLines: 3,
            decoration: InputDecoration(
              labelText: 'Book Description',
              labelStyle: TextStyle(
                color: isDark ? Colors.grey.shade400 : null,
              ),
              hintText: 'Describe what your book is about...',
              hintStyle: TextStyle(color: isDark ? Colors.grey.shade500 : null),
              border: const OutlineInputBorder(),
              prefixIcon: Icon(
                Icons.description,
                color: isDark ? Colors.grey.shade400 : null,
              ),
              enabledBorder: OutlineInputBorder(
                borderSide: BorderSide(
                  color: isDark ? Colors.grey.shade700 : Colors.grey.shade400,
                ),
              ),
              focusedBorder: OutlineInputBorder(
                borderSide: BorderSide(color: Colors.orange.shade700),
              ),
            ),
          ),
          const SizedBox(height: 20),
          DropdownButtonFormField<String>(
            value: _selectedField,
            style: TextStyle(color: isDark ? Colors.white : Colors.black),
            decoration: InputDecoration(
              labelText: 'Field of Study *',
              labelStyle: TextStyle(
                color: isDark ? Colors.grey.shade400 : null,
              ),
              border: const OutlineInputBorder(),
              prefixIcon: Icon(
                Icons.category,
                color: isDark ? Colors.grey.shade400 : null,
              ),
              enabledBorder: OutlineInputBorder(
                borderSide: BorderSide(
                  color: isDark ? Colors.grey.shade700 : Colors.grey.shade400,
                ),
              ),
              focusedBorder: OutlineInputBorder(
                borderSide: BorderSide(color: Colors.orange.shade700),
              ),
            ),
            dropdownColor: isDark ? Colors.grey.shade900 : Colors.white,
            items: _fieldConfigs.keys.map((field) {
              return DropdownMenuItem(
                value: field,
                child: Row(
                  children: [
                    Icon(
                      _fieldConfigs[field]!['icon'] as IconData,
                      color: _fieldConfigs[field]!['color'] as Color,
                    ),
                    const SizedBox(width: 10),
                    Text(
                      field,
                      style: TextStyle(
                        color: isDark ? Colors.white : Colors.black,
                      ),
                    ),
                  ],
                ),
              );
            }).toList(),
            onChanged: (value) {
              setState(() {
                _selectedField = value!;
              });
            },
          ),
          const SizedBox(height: 20),
          DropdownButtonFormField<String>(
            value: _selectedBookType,
            style: TextStyle(color: isDark ? Colors.white : Colors.black),
            decoration: InputDecoration(
              labelText: 'Book Type *',
              labelStyle: TextStyle(
                color: isDark ? Colors.grey.shade400 : null,
              ),
              border: const OutlineInputBorder(),
              prefixIcon: Icon(
                Icons.menu_book,
                color: isDark ? Colors.grey.shade400 : null,
              ),
              enabledBorder: OutlineInputBorder(
                borderSide: BorderSide(
                  color: isDark ? Colors.grey.shade700 : Colors.grey.shade400,
                ),
              ),
              focusedBorder: OutlineInputBorder(
                borderSide: BorderSide(color: Colors.orange.shade700),
              ),
            ),
            dropdownColor: isDark ? Colors.grey.shade900 : Colors.white,
            items: _bookTypeConfigs.keys.map((type) {
              return DropdownMenuItem(
                value: type,
                child: Row(
                  children: [
                    Icon(
                      _bookTypeConfigs[type]!['icon'] as IconData,
                      color: isDark ? Colors.white : null,
                    ),
                    const SizedBox(width: 10),
                    Text(
                      type,
                      style: TextStyle(
                        color: isDark ? Colors.white : Colors.black,
                      ),
                    ),
                  ],
                ),
              );
            }).toList(),
            onChanged: (value) {
              setState(() {
                _selectedBookType = value!;
              });
            },
          ),
          const SizedBox(height: 20),
          TextField(
            controller: _topicsController,
            style: TextStyle(color: isDark ? Colors.white : Colors.black),
            maxLines: 5,
            decoration: InputDecoration(
              labelText: 'Topics *',
              labelStyle: TextStyle(
                color: isDark ? Colors.grey.shade400 : null,
              ),
              hintText:
                  'Enter topics (one per line)\nExample:\nIntroduction to Algebra\nQuadratic Equations\nTrigonometry Basics',
              hintStyle: TextStyle(color: isDark ? Colors.grey.shade500 : null),
              border: const OutlineInputBorder(),
              prefixIcon: Icon(
                Icons.list,
                color: isDark ? Colors.grey.shade400 : null,
              ),
              enabledBorder: OutlineInputBorder(
                borderSide: BorderSide(
                  color: isDark ? Colors.grey.shade700 : Colors.grey.shade400,
                ),
              ),
              focusedBorder: OutlineInputBorder(
                borderSide: BorderSide(color: Colors.orange.shade700),
              ),
            ),
          ),
          const SizedBox(height: 10),
          Text(
            'Enter each topic on a new line. Each topic will become a chapter in your book.',
            style: TextStyle(
              fontSize: 12,
              color: isDark ? Colors.grey.shade400 : Colors.grey.shade600,
            ),
          ),
          const SizedBox(height: 30),
          ElevatedButton.icon(
            onPressed: _generateBook,
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.orange.shade700,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 40),
            ),
            icon: const Icon(Icons.auto_stories),
            label: const Text('Generate Book', style: TextStyle(fontSize: 16)),
          ),
          if (_generatedChapters.isNotEmpty && !_showDownloadButton) ...[
            const SizedBox(height: 30),
            const Text(
              'Generated Chapters Preview:',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 10),
            ..._generatedChapters.asMap().entries.map(
              (entry) => Card(
                margin: const EdgeInsets.only(bottom: 10),
                child: ListTile(
                  leading: CircleAvatar(
                    backgroundColor: Colors.orange.shade100,
                    child: Text('${entry.key + 1}'),
                  ),
                  title: Text(_topicsList[entry.key]),
                  subtitle: Text(
                    entry.value.length > 100
                        ? '${entry.value.substring(0, 100)}...'
                        : entry.value,
                    maxLines: 2,
                  ),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildGenerationScreen() {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          AnimatedBuilder(
            animation: _progressAnimation,
            builder: (context, child) {
              return Transform.translate(
                offset: Offset(0, -20 * _progressAnimation.value),
                child: Icon(
                  Icons.auto_stories,
                  size: 100,
                  color: Colors.orange.shade700,
                ),
              );
            },
          ),
          const SizedBox(height: 30),
          SizedBox(
            width: 200,
            child: LinearProgressIndicator(
              value: _generationProgress,
              backgroundColor: Colors.grey.shade300,
              valueColor: AlwaysStoppedAnimation<Color>(Colors.orange.shade700),
              minHeight: 8,
            ),
          ),
          const SizedBox(height: 20),
          Text(
            '${(_generationProgress * 100).toStringAsFixed(0)}% Complete',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: isDark ? Colors.white : Colors.black,
            ),
          ),
          const SizedBox(height: 10),
          Text(
            _currentStep,
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 14, color: Colors.grey.shade600),
          ),
          const SizedBox(height: 30),
          if (_topicsList.isNotEmpty)
            Text(
              'Chapter ${(_generationProgress * _topicsList.length).ceil()}/${_topicsList.length}',
              style: const TextStyle(fontSize: 16),
            ),
          const SizedBox(height: 30),
          ElevatedButton(
            onPressed: () {
              setState(() {
                _isGenerating = false;
              });
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.grey.shade300,
              foregroundColor: Colors.black,
            ),
            child: const Text('Cancel Generation'),
          ),
        ],
      ),
    );
  }
}
