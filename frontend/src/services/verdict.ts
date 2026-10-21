import type {ScanRecord} from '../types';
import {simpleResult,storedLanguage} from './resultLanguage.ts';
export function assessmentVerdict(scan:ScanRecord):string{return simpleResult(scan,storedLanguage()).title;}
