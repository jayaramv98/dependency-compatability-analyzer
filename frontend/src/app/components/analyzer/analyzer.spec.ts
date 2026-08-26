import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Analyzer } from './analyzer';

describe('Analyzer', () => {
  let component: Analyzer;
  let fixture: ComponentFixture<Analyzer>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Analyzer],
    }).compileComponents();

    fixture = TestBed.createComponent(Analyzer);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
