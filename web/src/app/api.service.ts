import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Result } from "./models/search-results";
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  http = inject(HttpClient);

  getFloorPrice(item_name: string){
    const url = `http://localhost:8000/wfmarkettool/item_floor_prices/${item_name}?oroder_count=5`;
    return this.http.get<Result>(url, {
      responseType: 'json',
      observe: "response",
    });
  }

}
