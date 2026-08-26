import { Routes } from '@angular/router';
import { AnalyzerComponent } from './components/analyzer/analyzer';

export const routes: Routes = [
    { path: '', component: AnalyzerComponent },
    { path: '**', redirectTo: '' }
];
