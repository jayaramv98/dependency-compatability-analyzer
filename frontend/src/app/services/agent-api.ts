import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment.development';

export interface QueryRequest {
    question: string;
}

export interface QueryResponse {
    summary: string;
    breaking_changes: string[];
    security_impact: string[];
    developer_actions: string[];
}

@Injectable({
    providedIn: 'root'
})
export class AgentApiService {
    private http = inject(HttpClient);

    // Dynamically pulls the base URL from the active environment file
    private baseUrl = environment.apiUrl;

    analyzeDependency(question: string): Observable<QueryResponse> {
        const payload: QueryRequest = { question };
        return this.http.post<QueryResponse>(`${this.baseUrl}/query`, payload);
    }
}