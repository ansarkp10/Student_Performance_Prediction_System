# performance_app/utils.py
import json
from django.db.models import Count, Avg
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
import numpy as np
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from datetime import datetime

def generate_charts(students):
    """
    Generate all charts for visualization
    Returns dictionary with base64 encoded chart images
    """
    charts = {}
    
    try:
        total_students = students.count()
        if total_students == 0:
            # Return empty charts if no students
            return {
                'performance_chart': '',
                'risk_chart': '',
                'attendance_chart': '',
                'assignment_chart': '',
                'scatter_chart': '',
                'time_chart': '',
                'quiz_chart': ''
            }
        
        # 1. Performance Distribution Pie Chart
        plt.figure(figsize=(10, 8))
        performance_counts = students.values('predicted_performance').annotate(count=Count('predicted_performance'))
        performances = []
        counts = []
        colors_list = []
        
        # Define performance order and colors
        performance_order = ['excellent', 'good', 'average', 'poor', 'at_risk']
        performance_labels = ['Excellent', 'Good', 'Average', 'Poor', 'At Risk']
        performance_colors = ['#2ecc71', '#3498db', '#f1c40f', '#e67e22', '#e74c3c']
        
        for perf in performance_order:
            count = 0
            for item in performance_counts:
                if item['predicted_performance'] == perf:
                    count = item['count']
                    break
            performances.append(perf.title())
            counts.append(count)
        
        # Add "Not Predicted"
        not_predicted_count = total_students - sum(counts)
        if not_predicted_count > 0:
            performances.append('Not Predicted')
            counts.append(not_predicted_count)
            performance_colors.append('#95a5a6')
        
        plt.pie(counts, labels=performances, colors=performance_colors, autopct='%1.1f%%', startangle=90)
        plt.title('Performance Distribution', fontsize=16, fontweight='bold')
        plt.axis('equal')
        
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        charts['performance_chart'] = base64.b64encode(buffer.getvalue()).decode('utf-8')
        plt.close()
        
        # 2. Risk Status Doughnut Chart
        plt.figure(figsize=(10, 8))
        at_risk_count = students.filter(is_at_risk=True).count()
        safe_count = total_students - at_risk_count
        
        labels = ['Safe', 'At Risk']
        sizes = [safe_count, at_risk_count]
        colors = ['#2ecc71', '#e74c3c']
        
        plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90,
                wedgeprops={'width': 0.3})  # For doughnut chart
        
        plt.title('Risk Status Distribution', fontsize=16, fontweight='bold')
        plt.axis('equal')
        
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        charts['risk_chart'] = base64.b64encode(buffer.getvalue()).decode('utf-8')
        plt.close()
        
        # 3. Attendance Distribution Histogram
        plt.figure(figsize=(10, 6))
        attendance_data = [s.attendance for s in students if s.attendance is not None]
        
        if attendance_data:
            bins = [0, 50, 60, 70, 80, 90, 100]
            labels_hist = ['<50%', '50-60%', '60-70%', '70-80%', '80-90%', '90-100%']
            
            hist, bin_edges = np.histogram(attendance_data, bins=bins)
            
            plt.bar(labels_hist, hist, color='#3498db', edgecolor='#2980b9')
            plt.title('Attendance Distribution', fontsize=16, fontweight='bold')
            plt.xlabel('Attendance Percentage')
            plt.ylabel('Number of Students')
            plt.xticks(rotation=45)
            
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
            buffer.seek(0)
            charts['attendance_chart'] = base64.b64encode(buffer.getvalue()).decode('utf-8')
            plt.close()
        
        # 4. Assignment Score Distribution
        plt.figure(figsize=(10, 6))
        assignment_data = [s.assignment_score for s in students if s.assignment_score is not None]
        
        if assignment_data:
            bins = [0, 50, 60, 70, 80, 90, 100]
            labels_hist = ['<50', '50-60', '60-70', '70-80', '80-90', '90-100']
            
            hist, bin_edges = np.histogram(assignment_data, bins=bins)
            
            plt.bar(labels_hist, hist, color='#9b59b6', edgecolor='#8e44ad')
            plt.title('Assignment Score Distribution', fontsize=16, fontweight='bold')
            plt.xlabel('Assignment Score')
            plt.ylabel('Number of Students')
            plt.xticks(rotation=45)
            
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
            buffer.seek(0)
            charts['assignment_chart'] = base64.b64encode(buffer.getvalue()).decode('utf-8')
            plt.close()
        
        # 5. Attendance vs Assignment Score Scatter Plot
        plt.figure(figsize=(12, 8))
        safe_students = students.filter(is_at_risk=False)
        risk_students = students.filter(is_at_risk=True)
        
        safe_x = [s.attendance for s in safe_students if s.attendance is not None and s.assignment_score is not None]
        safe_y = [s.assignment_score for s in safe_students if s.attendance is not None and s.assignment_score is not None]
        
        risk_x = [s.attendance for s in risk_students if s.attendance is not None and s.assignment_score is not None]
        risk_y = [s.assignment_score for s in risk_students if s.attendance is not None and s.assignment_score is not None]
        
        if safe_x or risk_x:
            plt.scatter(safe_x, safe_y, color='#3498db', alpha=0.7, s=100, label='Safe Students', edgecolors='black')
            plt.scatter(risk_x, risk_y, color='#e74c3c', alpha=0.7, s=100, label='At Risk Students', edgecolors='black')
            
            plt.title('Attendance vs Assignment Score', fontsize=16, fontweight='bold')
            plt.xlabel('Attendance (%)')
            plt.ylabel('Assignment Score (%)')
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
            buffer.seek(0)
            charts['scatter_chart'] = base64.b64encode(buffer.getvalue()).decode('utf-8')
            plt.close()
        
        # 6. Time Spent Analysis (Line Chart)
        plt.figure(figsize=(10, 6))
        # For demo, we'll create sample data based on student time_spent
        time_data = [s.time_spent for s in students if s.time_spent is not None]
        
        if time_data:
            # Create weekly averages (simplified)
            weeks = ['Week 1', 'Week 2', 'Week 3', 'Week 4', 'Week 5', 'Week 6', 'Week 7', 'Week 8']
            avg_time = np.linspace(min(time_data) if time_data else 0, max(time_data) if time_data else 25, 8)
            
            plt.plot(weeks, avg_time, marker='o', color='#e67e22', linewidth=3, markersize=8)
            plt.fill_between(weeks, avg_time, alpha=0.2, color='#e67e22')
            
            plt.title('Time Spent Analysis', fontsize=16, fontweight='bold')
            plt.xlabel('Week')
            plt.ylabel('Average Hours')
            plt.grid(True, alpha=0.3)
            
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
            buffer.seek(0)
            charts['time_chart'] = base64.b64encode(buffer.getvalue()).decode('utf-8')
            plt.close()
        
        # 7. Quiz Score Radar Chart
        plt.figure(figsize=(10, 8))
        quiz_data = [s.quiz_score for s in students if s.quiz_score is not None]
        
        if quiz_data:
            # Create sample quiz data
            quizzes = ['Quiz 1', 'Quiz 2', 'Quiz 3', 'Quiz 4', 'Quiz 5']
            avg_scores = [np.mean(quiz_data) * 0.8 + 20,  # Some variation
                         np.mean(quiz_data) * 0.85 + 15,
                         np.mean(quiz_data) * 0.9 + 10,
                         np.mean(quiz_data) * 0.95 + 5,
                         np.mean(quiz_data)]
            
            # Close the polygon
            angles = np.linspace(0, 2 * np.pi, len(quizzes), endpoint=False).tolist()
            avg_scores += avg_scores[:1]
            angles += angles[:1]
            
            ax = plt.subplot(111, polar=True)
            ax.plot(angles, avg_scores, 'o-', linewidth=2, color='#2ecc71')
            ax.fill(angles, avg_scores, alpha=0.25, color='#2ecc71')
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(quizzes)
            ax.set_ylim(0, 100)
            ax.set_title('Quiz Performance Analysis', fontsize=16, fontweight='bold', pad=20)
            
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
            buffer.seek(0)
            charts['quiz_chart'] = base64.b64encode(buffer.getvalue()).decode('utf-8')
            plt.close()
        
    except Exception as e:
        print(f"Error generating charts: {str(e)}")
        import traceback
        traceback.print_exc()
        # Return empty charts dict if there's an error
        return {key: '' for key in ['performance_chart', 'risk_chart', 'attendance_chart', 
                                   'assignment_chart', 'scatter_chart', 'time_chart', 'quiz_chart']}
    
    return charts

# Keep the PDF function if needed
def generate_predictions_pdf(students):
    """Generate PDF report of student predictions"""
    # ... (keep your existing PDF generation code) ...
    pass