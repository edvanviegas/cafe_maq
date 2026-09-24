# cafe_maq

# Sistema de Gerenciamento de Maquinário para Fazendas de Café

## Sobre o Projeto

Este projeto consiste no desenvolvimento de um sistema web voltado para proprietários de fazendas produtoras de café.

O sistema tem como objetivo auxiliar no gerenciamento das máquinas utilizadas na propriedade, no controle de manutenções, no acompanhamento das atividades realizadas pelos funcionários e no registro dos custos relacionados ao maquinário.

A proposta é centralizar essas informações em um único sistema, facilitando o acompanhamento da rotina da fazenda e permitindo que o proprietário tenha uma visão mais organizada sobre o funcionamento das máquinas e o trabalho realizado pelos funcionários.

## Objetivo

Desenvolver uma plataforma que permita ao proprietário da fazenda administrar seus funcionários, máquinas, atividades e manutenções, utilizando os registros realizados pelos funcionários para acompanhar o trabalho diário e identificar possíveis necessidades de manutenção.

O sistema também terá como objetivo auxiliar no acompanhamento dos custos de manutenção do maquinário.

## Tipos de Usuário

O sistema terá dois tipos principais de usuários:

### Dono da Fazenda

O proprietário terá acesso às funções administrativas do sistema, podendo:

* Cadastrar sua fazenda;
* Cadastrar e vincular funcionários;
* Cadastrar máquinas e equipamentos;
* Criar atividades para os funcionários;
* Definir atividades que devem ser realizadas;
* Acompanhar os relatórios enviados pelos funcionários;
* Consultar o histórico das atividades;
* Registrar e acompanhar manutenções;
* Acompanhar os custos de manutenção;
* Visualizar um resumo do desempenho das atividades.

### Funcionário

O funcionário terá acesso às funções relacionadas às atividades atribuídas pelo proprietário.

Ele poderá:

* Acessar a fazenda à qual foi vinculado;
* Visualizar as atividades atribuídas;
* Registrar o início e o término das atividades;
* Utilizar o sistema como uma forma de registro de ponto;
* Informar quais atividades foram realizadas;
* Preencher o relatório diário;
* Registrar problemas encontrados nas máquinas;
* Adicionar observações sobre o trabalho realizado.

## Principais Funcionalidades

### Cadastro da Fazenda

O proprietário poderá cadastrar as informações de sua fazenda e utilizar o sistema para administrar os dados relacionados à propriedade.

### Cadastro de Funcionários

O proprietário poderá cadastrar funcionários e vinculá-los à sua fazenda.

Após o vínculo, o funcionário poderá acessar as atividades destinadas a ele.

### Cadastro de Máquinas

O proprietário poderá registrar as máquinas utilizadas na fazenda, armazenando informações importantes para o acompanhamento do equipamento.

Entre as informações poderão estar:

* Nome da máquina;
* Tipo;
* Modelo;
* Marca;
* Ano;
* Identificação;
* Estado atual;
* Histórico de manutenção.

### Controle de Atividades

O proprietário poderá criar atividades que deverão ser realizadas pelos funcionários.

Os funcionários poderão visualizar as atividades atribuídas e registrar quando elas forem realizadas.

### Registro de Ponto e Atividades

O sistema permitirá registrar o horário de início e término das atividades.

Dessa forma, os registros poderão funcionar como uma forma de controle da jornada e das atividades realizadas durante o trabalho.

### Relatório Diário

Ao final das atividades, o funcionário poderá preencher um relatório informando o que foi realizado durante o dia.

O relatório poderá conter:

* Atividades realizadas;
* Horário de início;
* Horário de término;
* Máquina utilizada;
* Problemas identificados;
* Observações;
* Situação da atividade.

### Controle de Manutenção

O proprietário poderá registrar e acompanhar as manutenções realizadas nas máquinas.

O sistema poderá armazenar informações como:

* Máquina;
* Tipo de manutenção;
* Data;
* Descrição do serviço;
* Peças utilizadas;
* Responsável;
* Valor gasto;
* Próxima manutenção prevista.

### Controle de Custos

Os dados das manutenções serão utilizados para acompanhar os custos relacionados ao maquinário.

O proprietário poderá consultar informações como:

* Valor gasto por manutenção;
* Custo por máquina;
* Quantidade de manutenções;
* Histórico de gastos;
* Custo total em determinado período.

### Resumo de Desempenho

O proprietário terá acesso a uma área de resumo com informações sobre o funcionamento da propriedade.

Entre os dados apresentados poderão estar:

* Total de atividades;
* Atividades concluídas;
* Atividades pendentes;
* Horas registradas;
* Relatórios enviados;
* Máquinas em manutenção;
* Manutenções realizadas;
* Custos de manutenção.

## Banco de Dados

O sistema utilizará um banco de dados para armazenar as informações de forma organizada e permitir que os dados sejam consultados posteriormente.

Entre as principais informações armazenadas estarão:

* Usuários;
* Fazendas;
* Funcionários;
* Máquinas;
* Atividades;
* Registros de ponto;
* Relatórios;
* Manutenções;
* Custos.

Os registros ficarão relacionados entre si. Dessa forma, será possível identificar, por exemplo, qual funcionário realizou determinada atividade, em qual fazenda, utilizando qual máquina e em qual período.

## Tecnologias

O projeto será desenvolvido utilizando tecnologias para desenvolvimento web.

Tecnologias previstas:

* HTML;
* CSS;
* JavaScript;
* [Framework utilizado];
* MySQL
* Git;
* GitHub;
* Visual Studio Code.

Após o desenvolvimento e os testes, o sistema será preparado para hospedagem na HostGator.

## Estrutura da Sprint

Para o desenvolvimento do incremento da Sprint, as atividades serão divididas em tarefas menores e acompanhadas por meio de um quadro Kanban.

### A Fazer

* [ ] Criar sistema de login;
* [ ] Criar diferenciação entre dono e funcionário;
* [ ] Criar cadastro da fazenda;
* [ ] Criar cadastro de funcionários;
* [ ] Criar cadastro de máquinas;
* [ ] Criar cadastro de atividades;
* [ ] Criar formulário do funcionário;
* [ ] Criar registro de ponto;
* [ ] Criar relatório diário;
* [ ] Criar armazenamento dos dados no banco;
* [ ] Criar visualização dos relatórios;
* [ ] Criar resumo de desempenho;
* [ ] Criar controle de manutenção;
* [ ] Criar controle de custos;
* [ ] Realizar testes.

## Autores

Projeto desenvolvido por:
* Edvan Henrique Silva Viegas
* Hiago Rafael Fernandes do Amaral
