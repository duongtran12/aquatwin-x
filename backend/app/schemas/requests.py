from typing import Literal

from pydantic import BaseModel, Field, model_validator

from optimization.genetic import GeneticConfig
from simulation.engine import LeakScenario, RecoveryAction


class LeakScenarioPayload(BaseModel):
    pipe_id: str = Field(min_length=1)
    leak_area: float = Field(gt=0)
    start_time: int = Field(ge=0)
    end_time: int = Field(gt=0)
    split_position: float = Field(default=0.5, ge=0.05, le=0.95)
    discharge_coefficient: float = Field(default=0.75, gt=0, le=1)
    pressure_drop_threshold: float = Field(default=2.0, ge=0)

    @model_validator(mode="after")
    def validate_time_range(self) -> "LeakScenarioPayload":
        if self.end_time <= self.start_time:
            raise ValueError("end_time phải lớn hơn start_time")
        return self

    def to_domain(self) -> LeakScenario:
        return LeakScenario(**self.model_dump())


class RecoveryActionPayload(BaseModel):
    valve_id: str = Field(min_length=1)
    status: Literal["OPEN", "CLOSED"]

    def to_domain(self) -> RecoveryAction:
        return RecoveryAction(self.valve_id, self.status)


class BaselineSimulationRequest(BaseModel):
    network_id: str = "aquatwin_demo"


class FailureSimulationRequest(BaseModel):
    network_id: str = "aquatwin_demo"
    scenario: LeakScenarioPayload


class ManualRecoveryRequest(FailureSimulationRequest):
    actions: list[RecoveryActionPayload] = Field(min_length=1)


class OptimizationRequest(FailureSimulationRequest):
    algorithm: Literal["exhaustive", "ga"] = "ga"
    max_actions: int = Field(default=2, ge=0)
    top_k: int = Field(default=5, ge=1, le=50)
    population_size: int = Field(default=20, ge=2)
    generations: int = Field(default=20, ge=1)
    crossover_rate: float = Field(default=0.8, ge=0, le=1)
    mutation_rate: float = Field(default=0.1, ge=0, le=1)
    tournament_size: int = Field(default=3, ge=2)
    elite_count: int = Field(default=2, ge=1)
    seed: int = 42

    @model_validator(mode="after")
    def validate_genetic_parameters(self) -> "OptimizationRequest":
        if self.tournament_size > self.population_size:
            raise ValueError("tournament_size không được vượt population_size")
        if self.elite_count >= self.population_size:
            raise ValueError("elite_count phải nhỏ hơn population_size")
        return self

    def to_genetic_config(self) -> GeneticConfig:
        return GeneticConfig(
            population_size=self.population_size,
            generations=self.generations,
            crossover_rate=self.crossover_rate,
            mutation_rate=self.mutation_rate,
            tournament_size=self.tournament_size,
            elite_count=self.elite_count,
            max_actions=self.max_actions,
            seed=self.seed,
        )

