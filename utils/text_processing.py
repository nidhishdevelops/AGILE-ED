def generate_practical_steps(topic, sources):
    """Generate practical implementation steps with source references"""
    if not sources:
        return "Practical implementation steps could not be generated due to missing source information"
    
    # Identify different source types
    source_refs = {
        'ppt': [],
        'pdf': [],
        'doc': []
    }
    
    for s in sources:
        file_type = s.get('file_type', '').lower()
        original_file = s.get('original_file', '')
        location = s.get('location', '')
        
        if file_type == '.pdf':
            source_refs['pdf'].append(f"{original_file} ({location})")
        elif file_type == '.pptx':
            source_refs['ppt'].append(f"{original_file} ({location})")
        elif file_type == '.docx':
            source_refs['doc'].append(f"{original_file} ({location})")
    
    # Build source string
    source_str = []
    if source_refs['doc']:
        source_str.append(f"Syllabus: {', '.join(source_refs['doc'])}")
    if source_refs['ppt']:
        source_str.append(f"Lectures: {', '.join(source_refs['ppt'])}")
    if source_refs['pdf']:
        source_str.append(f"References: {', '.join(source_refs['pdf'])}")
    
    source_list = "\n".join(f"- {s}" for s in source_str)
    
    return f""
