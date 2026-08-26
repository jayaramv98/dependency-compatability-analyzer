import { Component, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormControl } from '@angular/forms';
import { finalize } from 'rxjs/operators';
import { AgentApiService, QueryResponse } from "../../services/agent-api";

@Component({
  selector: 'app-analyzer',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './analyzer.html',
  styleUrls: ['./analyzer.css']
})
export class AnalyzerComponent {
  private agentService = inject(AgentApiService);
  private cdr = inject(ChangeDetectorRef);

  // Standard reactive form control for the input
  queryControl = new FormControl('');

  result: QueryResponse | null = null;
  isLoading: boolean = false;
  errorMessage: string | null = null;

  runAnalysis(): void {
    const query = this.queryControl.value;
    if (!query || !query.trim()) return;

    this.isLoading = true;
    this.errorMessage = null;
    this.result = null;
    this.queryControl.disable(); // Programmatically disable the form control
    this.cdr.detectChanges();

    this.agentService.analyzeDependency(query)
      .pipe(
        finalize(() => {
          this.isLoading = false;
          this.queryControl.enable(); // Re-enable it when done
          this.cdr.detectChanges();
        })
      )
      .subscribe({
        next: (response) => {
          console.log('Received response from API:', response);
          this.result = response;
          this.cdr.detectChanges();
        },
        error: (err) => {
          console.error('API Error:', err);
          this.errorMessage = 'Failed to connect to the LangGraph backend. Ensure FastAPI is running.';
          this.cdr.detectChanges();
        }
      });
  }
}