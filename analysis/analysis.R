library(tidyverse)
library(RSQLite)

con <- dbConnect(RSQLite::SQLite(), "../dbs/cat-eval.db")

rs1 <- dbSendQuery(con, "SELECT * FROM content")
content <- dbFetch(rs1)

rs2 <- dbSendQuery(con, "SELECT * FROM grades")
grades <- dbFetch(rs2)

content <- content %>% 
  rowwise() %>% 
  mutate(answer_length = length(unlist(strsplit(answer, "\\s+"))))

content %>% 
  group_by(model) %>% 
  summarise(model_grade = mean(final_grade),
            sd = sd(final_grade)) %>% 
  arrange(desc(model_grade))

content %>% 
  group_by(model) %>% 
  summarise(mean_length = mean(answer_length),
            sd = sd(answer_length)) %>% 
  arrange(desc(mean_length))

grades %>% 
  group_by(evaluator) %>% 
  summarise(mean = mean(grade),
            sd = sd(grade)) %>% 
  arrange(desc(mean))

grades %>% 
  ggplot(aes(grade)) + 
  geom_histogram(aes(fill = evaluator), color = "black", binwidth = 1) +
  facet_wrap(~evaluator) +
  scale_x_continuous(limits = c(0, 10), breaks = seq(0, 10, 1)) +
  lims(y = c(0, 500)) +
  theme_minimal() +
  theme(legend.position = "none")

content %>% 
  ggplot(aes(final_grade)) + 
  geom_histogram(aes(fill = model), color = "black") + 
  scale_x_continuous(limits = c(0, 10), breaks = seq(0, 10, 1)) +
  theme_minimal() +
  theme(legend.position = "none") +
  facet_wrap(~model)

grades %>% 
  ggplot(aes(grade, evaluator)) + 
  geom_boxplot(aes(fill = evaluator)) + 
  geom_jitter(alpha = 0.1, height = 0.2) +
  scale_x_continuous(limits = c(0, 11), breaks = seq(0, 10, 1)) +
  theme_minimal() +
  theme(legend.position = "none")
