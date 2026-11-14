import { Routes } from '@angular/router';
import { DocumentPage } from './intake/document-page';
import { IntakePage } from './intake/intake-page';

export const routes: Routes = [
  { path: '', component: IntakePage, title: 'eLedgerCare – submit document' },
  { path: 'documents/:documentId', component: DocumentPage, title: 'eLedgerCare – document' },
  { path: '**', redirectTo: '' },
];
